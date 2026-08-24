"""
spawn_turtlebots.launch.py — Gazebo 로봇 스폰 하위 모듈
=========================================================
[역할] 마스터 런치(multi_bringup.launch.py)로부터 단 1대의 로봇 정보를
       인자로 넘겨받아, Gazebo 스폰과 robot_state_publisher를 실행합니다.
       이 파일을 직접 실행하지 말고 마스터 런치를 통해 호출하세요.

[핵심 처리 과정]
  1. SDF 모델 파일을 메모리에 읽어들임
  2. diff_drive 플러그인에 ROS 네임스페이스·odom·base_footprint 태그 주입
  3. 수정된 SDF를 임시 파일로 저장
  4. gazebo_ros/spawn_entity.py 노드로 Gazebo에 로봇 스폰
  5. robot_state_publisher 노드를 해당 네임스페이스에서 실행
"""

import os
import re
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


# ──────────────────────────────────────────────
# 모듈 수준에서 SDF 경로를 미리 계산 (launch_setup 반복 호출 방지)
# ──────────────────────────────────────────────
TURTLEBOT3_MODEL = os.environ.get('TURTLEBOT3_MODEL', 'waffle_pi')
_model_folder = 'turtlebot3_' + TURTLEBOT3_MODEL

SDF_PATH = os.path.join(
    get_package_share_directory('turtlebot3_gazebo'),
    'models',
    _model_folder,
    'model.sdf',
)

URDF_PATH = os.path.join(
    get_package_share_directory('turtlebot3_description'),
    'urdf',
    f'turtlebot3_{TURTLEBOT3_MODEL}.urdf',
)


def _inject_namespace_into_sdf(sdf_content: str, ns: str) -> str:
    """
    SDF diff_drive 플러그인 태그 내부에 ROS 네임스페이스 관련 태그를 주입합니다.
    기존 태그와의 충돌 및 중복을 방지하기 위해 기존 프레임 태그를 깨끗이 정리합니다.
    """
    plugin_pattern = r'(<plugin\s+name="[^"]*"[^>]*filename="libgazebo_ros_diff_drive\.so"[^>]*>|<plugin\s+name="[^"]*diff_drive[^"]*"[^>]*>)(.*?)(</plugin>)'

    def inject_ns(match):
        header = match.group(1)
        body   = match.group(2)
        footer = match.group(3)
        
        import re
        body = re.sub(r'<odometry_frame>.*?</odometry_frame>', '', body, flags=re.DOTALL)
        body = re.sub(r'<robot_base_frame>.*?</robot_base_frame>', '', body, flags=re.DOTALL)
        body = re.sub(r'<publish_odom>.*?</publish_odom>', '', body, flags=re.DOTALL)
        body = re.sub(r'<publish_odom_tf>.*?</publish_odom_tf>', '', body, flags=re.DOTALL)
        
        ros_match = re.search(r'<ros>(.*?)</ros>', body, flags=re.DOTALL)
        if ros_match:
            ros_inner = ros_match.group(1)
            new_ros = f'<ros>{ros_inner}\n      <remapping>tf:=/tf</remapping>\n    </ros>'
            body = re.sub(r'<ros>.*?</ros>', new_ros, body, count=1, flags=re.DOTALL)
        else:
            body = f'    <ros>\n      <remapping>tf:=/tf</remapping>\n    </ros>\n{body}'
            
        odom_tag = f'    <odometry_frame>{ns}/odom</odometry_frame>'
        base_tag = f'    <robot_base_frame>{ns}/base_footprint</robot_base_frame>'
        pub_tag  = f'    <publish_odom>true</publish_odom>\n    <publish_odom_tf>true</publish_odom_tf>'
        
        return f'{header}\n{odom_tag}\n{base_tag}\n{pub_tag}\n{body}{footer}'

    import re
    sdf_content = re.sub(plugin_pattern, inject_ns, sdf_content, flags=re.DOTALL)
    
    def inject_frame_prefix(match):
        frame = match.group(1)
        if not frame.startswith(ns + '/'):
            return f'<frame_name>{ns}/{frame}</frame_name>'
        return match.group(0)

    sdf_content = re.sub(r'<frame_name>\s*(.*?)\s*</frame_name>', inject_frame_prefix, sdf_content)
    
    return sdf_content


def launch_setup(context, *args, **kwargs):
    """OpaqueFunction 콜백: 런타임 인자를 확정하고 실행할 노드 목록을 반환합니다."""
    ns     = LaunchConfiguration('namespace').perform(context)
    x_pose = LaunchConfiguration('x_pose').perform(context)
    y_pose = LaunchConfiguration('y_pose').perform(context)
    z_pose = LaunchConfiguration('z_pose').perform(context)

    # ── 단계 1·2·3: SDF 네임스페이스 주입 및 임시 파일 저장 ──────────────
    with open(SDF_PATH, 'r') as f:
        sdf_content = f.read()

    sdf_content = _inject_namespace_into_sdf(sdf_content, ns)

    tmp_sdf_path = os.path.join(tempfile.gettempdir(), f'{ns}_model.sdf')
    with open(tmp_sdf_path, 'w') as f:
        f.write(sdf_content)

    # ── 단계 4: Gazebo에 로봇 스폰 ──────────────────────────────────────
    spawn_node = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        namespace=ns,
        arguments=[
            '-entity',           ns,
            '-file',             tmp_sdf_path,
            '-x',                x_pose,
            '-y',                y_pose,
            '-z',                z_pose,
            '-robot_namespace',  ns,
        ],
        output='screen',
    )

    # ── 단계 5: URDF 로드 및 robot_state_publisher 실행 ─────────────────
    if not os.path.exists(URDF_PATH):
        raise FileNotFoundError(f'URDF 파일을 찾을 수 없습니다: {URDF_PATH}')

    with open(URDF_PATH, 'r') as f:
        robot_desc = f.read()

    # URDF 내 ${namespace} 플레이스홀더 제거 (있을 경우 대비)
    robot_desc = robot_desc.replace('${namespace}', '')

    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        namespace=ns,
        output='screen',
        parameters=[{
            'use_sim_time':       True,
            'robot_description':  robot_desc,
            'frame_prefix':       ns + '/',
            'publish_frequency':  30.0,
        }],
        remappings=[
            ('tf', '/tf'),
            ('tf_static', '/tf_static'),
        ],
    )

    return [spawn_node, rsp_node]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='tb1',   description='로봇 네임스페이스'),
        DeclareLaunchArgument('x_pose',   default_value='-8.0',  description='Gazebo X 초기 위치 (m)'),
        DeclareLaunchArgument('y_pose',   default_value='-7.0',  description='Gazebo Y 초기 위치 (m)'),
        DeclareLaunchArgument('z_pose',   default_value='0.01',  description='Gazebo Z 초기 위치 (m)'),
        OpaqueFunction(function=launch_setup),
    ])
