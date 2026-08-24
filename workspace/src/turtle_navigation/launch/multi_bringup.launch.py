"""
multi_bringup.launch.py — 마스터 런치 파일
==========================================
[역할] 다중 로봇 환경의 단일 진입점(Single Entry Point).
       로봇 목록·위치 정보를 오직 이 파일 한 곳에서만 관리합니다.

[사용법]
  ros2 launch turtle_navigation multi_bringup.launch.py

[로봇 추가/변경 방법]
  아래 ROBOTS 리스트만 수정하면 Gazebo 스폰과 Nav2 실행이 자동으로 처리됩니다.
  각 항목의 키:
    name  - 로봇 네임스페이스 (예: tb1, tb2, ...)
    x, y  - Gazebo 내 초기 위치 (단위: 미터)
    yaw   - 초기 방향각 (단위: 라디안, 현재 spawn_turtlebots에서 미사용)
"""

"""
multi_bringup.launch.py — 마스터 런치 파일
==========================================
[역할] 다중 로봇 환경의 단일 진입점(Single Entry Point).
       로봇 목록·위치 정보를 오직 이 파일 한 곳에서만 관리합니다.
"""

import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import PushRosNamespace
from ament_index_python.packages import get_package_share_directory


# ──────────────────────────────────────────────
# [★ 핵심 설정 구역] 로봇을 추가하거나 위치를 바꿀 때 이 부분만 수정하세요!
# ──────────────────────────────────────────────
ROBOTS = [
    {'name': 'tb1', 'x': '-8.0', 'y': '-7.0', 'yaw': '0.0'},
    {'name': 'tb2', 'x': '-8.0', 'y': '-8.0', 'yaw': '0.0'},
    {'name': 'tb3', 'x': '-7.0', 'y': '-7.0', 'yaw': '0.0'},
    {'name': 'tb4', 'x': '-7.0', 'y': '-8.0', 'yaw': '0.0'},
]
# ──────────────────────────────────────────────

ROBOT_SPAWN_STAGGER_SEC = 3.0

def generate_launch_description():
    ld = LaunchDescription()

    turtle_gazebo_dir = get_package_share_directory('turtle_gazebo')
    turtle_nav_dir = get_package_share_directory('turtle_navigation')

    spawn_launch_path = os.path.join(
        turtle_gazebo_dir, 'launch', 'spawn_turtlebots.launch.py'
    )
    nav2_launch_path = os.path.join(
        turtle_nav_dir, 'launch', 'nav2_multi.launch.py'
    )

    for i, robot in enumerate(ROBOTS):
        ns = robot['name']

        # 1단계: Gazebo에 로봇 모델 스폰
        spawn_cmd = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(spawn_launch_path),
            launch_arguments={
                'namespace': ns,
                'x_pose':    robot['x'],
                'y_pose':    robot['y'],
                'z_pose':    '0.01',
            }.items(),
        )

        # 2단계: Nav2 스택 실행 (★ GroupAction과 PushRosNamespace로 네임스페이스 강제 주입!)
        nav2_cmd = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav2_launch_path),
            launch_arguments={
                'namespace': ns,
            }.items(),
        )

        # 3단계: 타이머를 이용한 스태거링 (충돌 방지)
        delayed_group = TimerAction(
            period=i * ROBOT_SPAWN_STAGGER_SEC,
            actions=[spawn_cmd, nav2_cmd],
        )
        ld.add_action(delayed_group)

    return ld