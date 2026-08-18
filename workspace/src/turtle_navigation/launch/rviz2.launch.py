import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """
    RViz2 실행 런치 파일 (다중 터틀봇 시각화)
    - 각 로봇의 TF, LiDAR, 경로 등을 한 화면에 시각화
    """
    rviz_config = os.path.join(
        get_package_share_directory('turtle_navigation'),
        'config',
        'multi_robot_rviz.rviz'
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config] if os.path.exists(rviz_config) else [],
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([rviz_node])
