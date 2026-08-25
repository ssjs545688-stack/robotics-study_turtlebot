"""
nav2_multi.launch.py — Nav2 내비게이션 스택 하위 모듈
======================================================
[수정 내용]
 1. base_link 및 map 프레임 치환 구문 추가 (tb1/base_link, tb1/odom)
 2. Map Server 없이도 작동하도록 map -> {ns}/odom Static TF Publisher 추가
"""

import os
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, IncludeLaunchDescription, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import SetRemap, PushRosNamespace, Node


def launch_setup(context, *args, **kwargs):
    ns = LaunchConfiguration('namespace').perform(context)

    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    turtle_nav_dir   = get_package_share_directory('turtle_navigation')
    nav2_params_path = os.path.join(turtle_nav_dir, 'config', 'nav2_params.yaml')

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: YAML 텍스트 치환 (base_link, odom, map 모두 네임스페이스 적용)
    # ─────────────────────────────────────────────────────────────────────────
    with open(nav2_params_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Frame ID 치환 (base_link, base_footprint, odom)
    content = content.replace('robot_base_frame: base_link', f'robot_base_frame: {ns}/base_link')
    content = content.replace('robot_base_frame: "base_link"', f'robot_base_frame: "{ns}/base_link"')
    content = content.replace('robot_base_frame: base_footprint', f'robot_base_frame: {ns}/base_footprint')
    content = content.replace('robot_base_frame: "base_footprint"', f'robot_base_frame: "{ns}/base_footprint"')
    
    content = content.replace('global_frame: odom', f'global_frame: {ns}/odom')
    content = content.replace('global_frame: "odom"', f'global_frame: "{ns}/odom"')
    content = content.replace('global_frame: map', f'global_frame: {ns}/odom')  # map 프레임 대신 odom 활용
    content = content.replace('global_frame: "map"', f'global_frame: "{ns}/odom"')

    content = content.replace('base_frame_id: base_footprint', f'base_frame_id: {ns}/base_footprint')
    content = content.replace('base_frame_id: "base_footprint"', f'base_frame_id: "{ns}/base_footprint"')
    content = content.replace('base_frame_id: base_link', f'base_frame_id: {ns}/base_link')
    content = content.replace('base_frame_id: "base_link"', f'base_frame_id: "{ns}/base_link"')

    content = content.replace('odom_frame_id: odom', f'odom_frame_id: {ns}/odom')
    content = content.replace('odom_frame_id: "odom"', f'odom_frame_id: "{ns}/odom"')

    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml', delete=False, encoding='utf-8',
        prefix=f'nav2_params_{ns}_',
    )
    tmp.write(content)
    tmp.flush()
    tmp.close()
    params_file_path = tmp.name

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: navigation_launch.py 실행 설정
    # ─────────────────────────────────────────────────────────────────────────
    nav2_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'namespace':       ns,
            'use_namespace':   'False',
            'use_sim_time':    'True',
            'params_file':     params_file_path,
            'autostart':       'True',
            'use_composition': 'False',
            'use_respawn':     'False',
        }.items(),
    )

    # map -> {ns}/odom 연결을 위한 Static TF Publisher 노드
    static_tf_pub = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='map_to_odom_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'map', f'{ns}/odom'],
        output='screen'
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: 네임스페이스 및 리매핑 적용
    # ─────────────────────────────────────────────────────────────────────────
    nav2_group = GroupAction([
        PushRosNamespace(ns),
        SetRemap(src='/tf',        dst='tf'),
        SetRemap(src='/tf_static', dst='tf_static'),
        SetRemap(src='clock',     dst='/clock'),
        static_tf_pub,
        nav2_cmd,
    ])

    return [nav2_group]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace',
            default_value='tb1',
            description='Nav2 스택을 실행할 로봇 네임스페이스',
        ),
        OpaqueFunction(function=launch_setup),
    ])