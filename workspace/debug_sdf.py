import os
import tempfile
import sys
import re

# Simulate what the launch file does
ns = 'tb1'
sdf_path = r'C:\opt\ros\humble\share\turtlebot3_gazebo\models\turtlebot3_waffle_pi\model.sdf'
if not os.path.exists(sdf_path):
    print("Could not find sdf file in C:\opt\ros\humble")
    # try other common paths
    paths = [
        r'C:\dev\ros2_humble\share\turtlebot3_gazebo\models\turtlebot3_waffle_pi\model.sdf',
        r'c:\work\turtlebot\workspace\install\turtlebot3_gazebo\share\turtlebot3_gazebo\models\turtlebot3_waffle_pi\model.sdf',
        r'c:\work\turtlebot\workspace\src\turtlebot3_simulations\turtlebot3_gazebo\models\turtlebot3_waffle_pi\model.sdf'
    ]
    for p in paths:
        if os.path.exists(p):
            sdf_path = p
            break
    else:
        print("SDF not found anywhere!")
        sys.exit(1)

with open(sdf_path, 'r') as f:
    sdf_content = f.read()

plugin_pattern = r'(<plugin\s+name="[^"]*"[^>]*filename="libgazebo_ros_diff_drive\.so"[^>]*>|<plugin\s+name="[^"]*diff_drive[^"]*"[^>]*>)(.*?)(</plugin>)'

def inject_ns(match):
    header = match.group(1)
    body   = match.group(2)
    footer = match.group(3)
    
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

sdf_content = re.sub(plugin_pattern, inject_ns, sdf_content, flags=re.DOTALL)

def inject_frame_prefix(match):
    frame = match.group(1)
    if not frame.startswith(ns + '/'):
        return f'<frame_name>{ns}/{frame}</frame_name>'
    return match.group(0)

sdf_content = re.sub(r'<frame_name>\s*(.*?)\s*</frame_name>', inject_frame_prefix, sdf_content)

print(sdf_content)
