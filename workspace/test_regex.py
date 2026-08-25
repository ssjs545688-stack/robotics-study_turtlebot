import re

sdf_content = """
<sdf version="1.6">
  <model name="turtlebot3_waffle_pi">
    <plugin name="turtlebot3_diff_drive" filename="libgazebo_ros_diff_drive.so">
      <ros>
        <!-- <namespace>/tb3</namespace> -->
      </ros>

      <update_rate>30</update_rate>
      <odometry_frame>odom</odometry_frame>
      <robot_base_frame>base_footprint</robot_base_frame>
      <publish_odom>true</publish_odom>
      <publish_odom_tf>true</publish_odom_tf>
    </plugin>
  </model>
</sdf>
"""

ns = 'tb1'
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

with open("test_sdf.xml", "w") as f:
    f.write(sdf_content)
print("Done")
