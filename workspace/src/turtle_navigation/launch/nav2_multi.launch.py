"""
nav2_multi.launch.py — Nav2 내비게이션 스택 하위 모듈
======================================================
[수정 내용]
 1. base_link 및 map 프레임 치환 구문 추가 (tb1/base_link, tb1/odom)
 2. 맵 파일(warehouse_map.yaml)이 존재하면 map 프레임 사용,
    없으면 {ns}/odom을 fallback으로 사용
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
    
    # ─────────────────────────────────────────────────────────────────────────
    # 맵 파일 존재 여부에 따라 global_frame 동적 결정
    # - 맵이 있으면: map 프레임 사용 (정적 맵 기반 그로벌 플래닝)
    # - 맵이 없으면: {ns}/odom 프레임 fallback (슬램 모드)
    # ─────────────────────────────────────────────────────────────────────────
    map_yaml_path = os.path.join(
        get_package_share_directory('turtle_navigation'),
        'maps', 'warehouse_map.yaml'
    )
    use_static_map = os.path.isfile(map_yaml_path)

    if use_static_map:
        print(f'[nav2_multi] [{ns}] 정적 맵 발견! map 프레임으로 내비게이션 실행')
        content = content.replace('global_frame: odom', 'global_frame: map')
        content = content.replace('global_frame: "odom"', 'global_frame: "map"')
        # map → map 은 이미 맞으므로 추가 치환 불필요
    else:
        print(f'[nav2_multi] [{ns}] 맵 없음. {ns}/odom fallback 사용 (먼저 mapping.launch.py로 맵을 만드세요!)')
        content = content.replace('global_frame: odom', f'global_frame: {ns}/odom')
        content = content.replace('global_frame: "odom"', f'global_frame: "{ns}/odom"')
        content = content.replace('global_frame: map', f'global_frame: {ns}/odom')
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
    nodes_to_start = [
        PushRosNamespace(ns),
        SetRemap(src='/tf',        dst='tf'),
        SetRemap(src='/tf_static', dst='tf_static'),
        SetRemap(src='clock',     dst='/clock'),
        static_tf_pub,
        nav2_cmd,
    ]

    # 맵 파일이 있을 경우 맵 서버와 해당 라이프사이클 매니저를 추가
    if use_static_map:
        map_server_node = Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            output='screen',
            parameters=[{'yaml_filename': map_yaml_path, 'use_sim_time': True}]
        )
        lifecycle_manager_map = Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_map',
            output='screen',
            parameters=[{'use_sim_time': True},
                        {'autostart': True},
                        {'node_names': ['map_server']}]
        )
        nodes_to_start.extend([map_server_node, lifecycle_manager_map])

    nav2_group = GroupAction(nodes_to_start)

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