import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace

def generate_launch_description():
    # Get the urdf file
    TURTLEBOT3_MODEL = os.environ['TURTLEBOT3_MODEL']
    model_folder = 'turtlebot3_' + TURTLEBOT3_MODEL
    urdf_path = os.path.join(
        get_package_share_directory('turtlebot3_gazebo'),
        'models',
        model_folder,
        'model.sdf'
    )

    # Robot poses (4 robots in standby zone near -8, -8)
    robots = [
        {'name': 'tb1', 'x_pose': '-8.0', 'y_pose': '-7.0', 'z_pose': '0.01'},
        {'name': 'tb2', 'x_pose': '-8.0', 'y_pose': '-8.0', 'z_pose': '0.01'},
        {'name': 'tb3', 'x_pose': '-7.0', 'y_pose': '-7.0', 'z_pose': '0.01'},
        {'name': 'tb4', 'x_pose': '-7.0', 'y_pose': '-8.0', 'z_pose': '0.01'}
    ]

    ld = LaunchDescription()

    for robot in robots:
        spawn_turtlebot_cmd = Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-entity', robot['name'],
                '-file', urdf_path,
                '-x', robot['x_pose'],
                '-y', robot['y_pose'],
                '-z', robot['z_pose'],
                '-robot_namespace', robot['name']
            ],
            output='screen',
        )

        urdf_file_path = os.path.join(
            get_package_share_directory('turtlebot3_description'),
            'urdf',
            f'turtlebot3_{TURTLEBOT3_MODEL}.urdf'
        )
        
        with open(urdf_file_path, 'r') as infp:
            robot_desc = infp.read()

        robot_state_publisher_cmd = Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            namespace=robot['name'],
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'robot_description': robot_desc,
                'frame_prefix': robot['name'] + '/'
            }]
        )

        ld.add_action(spawn_turtlebot_cmd)
        ld.add_action(robot_state_publisher_cmd)

    return ld
