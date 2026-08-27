#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from gazebo_msgs.srv import SpawnEntity, DeleteEntity
from geometry_msgs.msg import Pose
import uuid

# 3kg 박스 모델 (Gazebo SDF)
BOX_SDF = """<?xml version="1.0" ?>
<sdf version="1.6">
  <model name="{model_name}">
    <static>false</static>
    <link name="link">
      <inertial>
        <mass>3.0</mass>
        <inertia>
          <ixx>0.01</ixx> <ixy>0.0</ixy> <ixz>0.0</ixz>
          <iyy>0.01</iyy> <iyz>0.0</iyz>
          <izz>0.01</izz>
        </inertia>
      </inertial>
      <collision name="collision">
        <geometry><box><size>0.2 0.2 0.2</size></box></geometry>
        <surface>
          <friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction>
        </surface>
      </collision>
      <visual name="visual">
        <geometry><box><size>0.2 0.2 0.2</size></box></geometry>
        <material>
          <ambient>0.8 0.6 0.4 1</ambient>
          <diffuse>0.8 0.6 0.4 1</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>
"""

class ScenarioManager(Node):
    def __init__(self):
        super().__init__('scenario_manager')
        
        self.spawn_client = self.create_client(SpawnEntity, '/spawn_entity')
        self.delete_client = self.create_client(DeleteEntity, '/delete_entity')
        
        self.create_subscription(String, '/scenario/spawn_cargo', self.spawn_cb, 10)
        self.create_subscription(String, '/scenario/despawn_cargo', self.despawn_cb, 10)
                
        self.robot_cargo = {} # 로봇 ID에 매핑된 화물 이름 추적
        self.get_logger().info("Scenario Manager initialized. Waiting for spawn/despawn requests...")

    def spawn_cb(self, msg):
        # msg.data 포맷: "robot_id,x,y" (예: "tb1,-7.5,8.5")
        try:
            parts = msg.data.split(',')
            robot_id = parts[0]
            target_x = float(parts[1])
            target_y = float(parts[2])
        except Exception as e:
            self.get_logger().error(f"Invalid spawn message format: {msg.data}, Error: {e}")
            return
            
        if not self.spawn_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("SpawnEntity service not available")
            return
            
        # 지정된 좌표 위(z=0.3)에 박스 생성
        spawn_pose = Pose()
        spawn_pose.position.x = target_x
        spawn_pose.position.y = target_y
        spawn_pose.position.z = 0.3
        spawn_pose.orientation.w = 1.0
        
        cargo_name = f"cargo_box_{uuid.uuid4().hex[:8]}"
        self.robot_cargo[robot_id] = cargo_name
        
        req = SpawnEntity.Request()
        req.name = cargo_name
        req.xml = BOX_SDF.replace("{model_name}", cargo_name)
        req.robot_namespace = ""
        req.initial_pose = spawn_pose
        req.reference_frame = "world"
        
        self.get_logger().info(f"Spawning {cargo_name} for {robot_id} at ({target_x}, {target_y})")
        self.spawn_client.call_async(req)

    def despawn_cb(self, msg):
        robot_id = msg.data
        cargo_name = self.robot_cargo.get(robot_id)
        if not cargo_name:
            self.get_logger().warn(f"No active cargo tracked for {robot_id}")
            return
            
        if not self.delete_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("DeleteEntity service not available")
            return
            
        req = DeleteEntity.Request()
        req.name = cargo_name
        
        self.get_logger().info(f"Despawning {cargo_name} for {robot_id}")
        self.delete_client.call_async(req)
        del self.robot_cargo[robot_id]

def main(args=None):
    rclpy.init(args=args)
    node = ScenarioManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
