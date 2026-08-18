import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():
    # 패키지 디렉토리
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    turtle_nav_dir = get_package_share_directory('turtle_navigation')

    nav2_params = os.path.join(turtle_nav_dir, 'config', 'nav2_params.yaml')

    # 로봇 목록 (네임스페이스 + 초기 위치)
    robots = [
        {'name': 'tb1', 'x': '-8.0', 'y': '-7.0', 'yaw': '0.0'},
        {'name': 'tb2', 'x': '-8.0', 'y': '-8.0', 'yaw': '0.0'},
        {'name': 'tb3', 'x': '-7.0', 'y': '-7.0', 'yaw': '0.0'},
        # tb4는 예비 자원 - 기본만 띄움
        {'name': 'tb4', 'x': '-7.0', 'y': '-8.0', 'yaw': '0.0'},
    ]

    ld = LaunchDescription()

    for robot in robots:
        ns = robot['name']

        # 각 로봇별 Nav2 bringup (SLAM 모드 - 맵 없이 탐색)
        nav2_cmd = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
            ),
            launch_arguments={
                'namespace': ns,
                'use_namespace': 'True',
                'slam': 'True',         # 맵 없이 SLAM으로 실시간 맵핑
                'map': '',
                'use_sim_time': 'True',
                'params_file': nav2_params,
                'autostart': 'True',
                'use_composition': 'False',
                'use_respawn': 'False',
            }.items()
        )

        ld.add_action(nav2_cmd)

    return ld
