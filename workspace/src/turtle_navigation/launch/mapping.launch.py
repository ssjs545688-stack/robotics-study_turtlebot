"""
mapping.launch.py — 창고 맵 빌드 전용 런치 파일
================================================
[역할]
  slam_toolbox를 이용해 tb1 로봇 단 1대로 창고 전체를 탐색하며
  2D 점유격자 맵(Occupancy Grid Map)을 생성합니다.

[사용법]
  1. Gazebo 실행 (별도 터미널):
       ros2 launch turtle_gazebo warehouse.launch.py

  2. 맵 빌드 실행 (이 파일):
       ros2 launch turtle_navigation mapping.launch.py

  3. teleop으로 창고 전체를 수동 주행 (별도 터미널):
       ros2 run teleop_twist_keyboard teleop_twist_keyboard \
         --ros-args --remap cmd_vel:=/tb1/cmd_vel

  4. 맵 저장 (창고 전체를 다 돌아다닌 후, 별도 터미널):
       source ~/ros2_ws/install/setup.bash
       ros2 run nav2_map_server map_saver_cli \
         -f ~/ros2_ws/src/turtle_navigation/maps/warehouse_map \
         --ros-args -p use_sim_time:=True
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node


MAPPING_ROBOT_NS = 'tb1'
MAPPING_ROBOT_X  = '-8.0'
MAPPING_ROBOT_Y  = '-7.0'


def generate_launch_description():
    turtle_gazebo_dir = get_package_share_directory('turtle_gazebo')
    turtle_nav_dir    = get_package_share_directory('turtle_navigation')
    ns = MAPPING_ROBOT_NS

    spawn_launch_path = os.path.join(
        turtle_gazebo_dir, 'launch', 'spawn_turtlebots.launch.py'
    )

    # ─────────────────────────────────────────────────────────────────
    # 1단계: tb1 로봇 단 1대를 Gazebo에 스폰
    # ─────────────────────────────────────────────────────────────────
    spawn_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(spawn_launch_path),
        launch_arguments={
            'namespace': ns,
            'x_pose':    MAPPING_ROBOT_X,
            'y_pose':    MAPPING_ROBOT_Y,
            'z_pose':    '0.01',
        }.items(),
    )

    # ─────────────────────────────────────────────────────────────────
    # 2단계: TF 릴레이
    #   spawn_turtlebots.launch.py 는 tf/tf_static 을 네임스페이스 로컬로
    #   퍼블리시합니다 (/{ns}/tf). slam_toolbox 는 글로벌 /tf 를 구독하므로
    #   직접 만든 tf_relay.py 로 중계해 TF 체인을 연결합니다.
    # ─────────────────────────────────────────────────────────────────
    tf_relay_node = Node(
        package='turtle_navigation',
        executable='tf_relay.py',
        name='tf_relay',
        parameters=[{
            'namespace': ns,
            'use_sim_time': True,  # [Fix 1] 시뮬레이션 시간 기준으로 동작
        }],
        output='screen',
    )

    # ─────────────────────────────────────────────────────────────────
    # 3단계: slam_toolbox (Online Async Mode)
    # ─────────────────────────────────────────────────────────────────
    slam_params = {
        'use_sim_time':             True,   # [Fix 1] 시뮤 타임 사용
        'base_frame':               f'{ns}/base_footprint',
        'odom_frame':               f'{ns}/odom',
        'map_frame':                'map',
        'scan_topic':               f'/{ns}/scan',
        'mode':                     'mapping',
        # 맵 품질 설정
        'resolution':               0.05,
        'max_laser_range':          20.0,
        'minimum_travel_distance':  0.3,
        'minimum_travel_heading':   0.3,
        'map_update_interval':      2.0,
        'do_loop_closing':          True,
        # [Fix 2] TF 타임아웃 및 버퍼 대폭 확장 — 시뮬레이션 지연 보정
        'transform_timeout':        2.0,    # TF 대기 시간 (1.0 → 2.0초)
        'tf_buffer_duration':       60.0,   # TF 버퍼 크기 (30 → 60초)
        # [Fix 3] 메시지 큐 크기 확장 — 시뮬레이션 보통 시 처리 속도 부족 대비
        'scan_queue_size':          50,     # 라이다 메시지 큐 (default: 10 → 50)
        'transform_publish_period': 0.02,   # TF 퍼블리시 주기 (50Hz)
    }

    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[slam_params],
    )

    # ─────────────────────────────────────────────────────────────────
    # 4단계: RViz2 (맵 빌드 시각화)
    # ─────────────────────────────────────────────────────────────────
    rviz_config = os.path.join(turtle_nav_dir, 'config', 'mapping_rviz.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],  # [Fix 1] 시뮤 타임 사용
        output='screen',
    )

    return LaunchDescription([
        # 로봇 스폰 먼저
        spawn_cmd,
        # 3초 후 TF 릴레이 실행 (robot_state_publisher 안정화 대기)
        TimerAction(
            period=3.0,
            actions=[tf_relay_node],
        ),
        # 5초 후 SLAM 실행 (TF 릴레이 안정화 대기)
        TimerAction(
            period=5.0,
            actions=[slam_node],
        ),
        # 6초 후 RViz 실행
        TimerAction(
            period=6.0,
            actions=[rviz_node],
        ),
    ])
