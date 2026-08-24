"""
nav2_multi.launch.py — Nav2 내비게이션 스택 하위 모듈
======================================================
[수정 사항]
 - PyYAML의 yaml.dump()가 한 줄 배열[...]을 여러 줄 블록(-)으로 강제 재변환하여
   RewrittenYaml에서 critics가 유실되는 문제를 해결하기 위해,
   텍스트 직접 읽기/치환 방식(replace)으로 파라미터 임시 파일을 생성합니다.
"""

import os
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, OpaqueFunction,
    IncludeLaunchDescription, GroupAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import SetRemap


def launch_setup(context, *args, **kwargs):
    """OpaqueFunction 콜백: namespace를 확정한 뒤 Nav2 런치를 구성합니다."""
    ns = LaunchConfiguration('namespace').perform(context)

    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    turtle_nav_dir   = get_package_share_directory('turtle_navigation')
    nav2_params_path = os.path.join(turtle_nav_dir, 'config', 'nav2_params.yaml')

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: 원본 YAML을 텍스트로 직접 읽어 프레임 이름만 치환
    # (PyYAML dump로 인한 inline 배열 formatting 파괴 방지)
    # ─────────────────────────────────────────────────────────────────────────
    with open(nav2_params_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 프레임 설정 치환
    content = content.replace('global_frame: odom', f'global_frame: {ns}/odom')
    content = content.replace('global_frame: "odom"', f'global_frame: "{ns}/odom"')
    content = content.replace('robot_base_frame: base_footprint', f'robot_base_frame: {ns}/base_footprint')
    content = content.replace('robot_base_frame: "base_footprint"', f'robot_base_frame: "{ns}/base_footprint"')
    content = content.replace('base_frame_id: base_footprint', f'base_frame_id: {ns}/base_footprint')
    content = content.replace('base_frame_id: "base_footprint"', f'base_frame_id: "{ns}/base_footprint"')
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
    # Step 2: navigation_launch.py 호출
    # ─────────────────────────────────────────────────────────────────────────
    nav2_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'namespace':       ns,
            'use_namespace':   'True',
            'use_sim_time':    'True',
            'params_file':     params_file_path,
            'autostart':       'True',
            'use_composition': 'False',
            'use_respawn':     'False',
        }.items(),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: TF 및 Clock 글로벌 연결
    # ─────────────────────────────────────────────────────────────────────────
    nav2_group = GroupAction([
        SetRemap(src='tf',        dst='/tf'),
        SetRemap(src='tf_static', dst='/tf_static'),
        SetRemap(src='clock',     dst='/clock'),
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