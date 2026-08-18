#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
import time
import math

# 사전 정의된 주요 구역 (Zone) 좌표
ZONES = {
    'standby': {'x': -8.0, 'y': -8.0, 'yaw': 0.0},
    'loading': {'x': -7.5, 'y': 8.5, 'yaw': math.pi/2},
    'unload_A': {'x': 8.5, 'y': 7.5, 'yaw': 0.0},
    'unload_B': {'x': 8.5, 'y': 0.0, 'yaw': 0.0},
    'unload_C': {'x': 8.5, 'y': -7.5, 'yaw': 0.0}
}

class FmsNode(Node):
    def __init__(self):
        super().__init__('fms_node')
        self.get_logger().info('Initializing Fleet Management System (FMS) Node')

        # 로봇 상태 관리
        self.fleet_status = {
            'tb1': {'state': 'IDLE', 'current_target': None, 'battery': 100},
            'tb2': {'state': 'IDLE', 'current_target': None, 'battery': 95},
            'tb3': {'state': 'IDLE', 'current_target': None, 'battery': 80},
            'tb4': {'state': 'CHARGING', 'current_target': None, 'battery': 20} # tb4는 예비 자원으로 가정
        }

        # Action Clients 생성 (Nav2)
        self.nav_clients = {}
        for robot_id in self.fleet_status.keys():
            action_topic = f'/{robot_id}/navigate_to_pose'
            client = ActionClient(self, NavigateToPose, action_topic)
            self.nav_clients[robot_id] = client

        # 작업 큐: (작업 목적지, 우선순위)
        self.pending_tasks = ['loading', 'loading', 'loading']
        self.task_destinations = ['unload_A', 'unload_B', 'unload_C']

        # 5초마다 작업 할당 평가 루프 실행
        self.timer = self.create_timer(5.0, self.task_allocation_loop)

    def euler_to_quaternion(self, yaw):
        return [0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)]

    def create_pose_stamped(self, target_zone):
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        coords = ZONES[target_zone]
        pose.pose.position.x = coords['x']
        pose.pose.position.y = coords['y']
        
        q = self.euler_to_quaternion(coords['yaw'])
        pose.pose.orientation.x = q[0]
        pose.pose.orientation.y = q[1]
        pose.pose.orientation.z = q[2]
        pose.pose.orientation.w = q[3]
        return pose

    def task_allocation_loop(self):
        idle_robots = [r for r, status in self.fleet_status.items() if status['state'] == 'IDLE']
        
        if not self.pending_tasks:
            # 적재 구역 대기열이 비었으면 하역 구역 작업으로 전환
            if self.task_destinations:
                self.pending_tasks = self.task_destinations
                self.task_destinations = []
                self.get_logger().info('Switching phase: Moving to Unload Zones')
            else:
                self.get_logger().info('All tasks completed. Returning to standby.')
                self.pending_tasks = ['standby', 'standby', 'standby']

        for robot_id in idle_robots:
            if not self.pending_tasks:
                break
                
            # 가장 가용한 로봇에게 첫 번째 작업 할당
            target_zone = self.pending_tasks.pop(0)
            self.get_logger().info(f'Allocating task to {robot_id}: Go to [{target_zone}]')
            
            # 상태 업데이트
            self.fleet_status[robot_id]['state'] = 'MOVING'
            self.fleet_status[robot_id]['current_target'] = target_zone
            
            # Nav2 Goal 전송
            self.send_nav_goal(robot_id, target_zone)

    def send_nav_goal(self, robot_id, target_zone):
        client = self.nav_clients[robot_id]
        if not client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error(f'Nav2 Action server not available for {robot_id}')
            self.fleet_status[robot_id]['state'] = 'IDLE'  # 롤백
            self.pending_tasks.insert(0, target_zone)
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self.create_pose_stamped(target_zone)

        self.get_logger().info(f'Sending {robot_id} to {target_zone}...')
        send_goal_future = client.send_goal_async(goal_msg, feedback_callback=lambda msg: self.feedback_cb(robot_id, msg))
        send_goal_future.add_done_callback(lambda future: self.goal_response_cb(future, robot_id, target_zone))

    def goal_response_cb(self, future, robot_id, target_zone):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn(f'Goal rejected for {robot_id}')
            self.fleet_status[robot_id]['state'] = 'IDLE'
            return

        self.get_logger().info(f'Goal accepted for {robot_id}')
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(lambda future: self.get_result_cb(future, robot_id, target_zone))

    def feedback_cb(self, robot_id, feedback_msg):
        # 거리 등 상태 모니터링 가능
        pass

    def get_result_cb(self, future, robot_id, target_zone):
        result = future.result().result
        status = future.result().status
        
        if status == 4: # SUCCEEDED
            self.get_logger().info(f'{robot_id} arrived at {target_zone} successfully!')
            self.fleet_status[robot_id]['state'] = 'IDLE'
            self.fleet_status[robot_id]['current_target'] = None
            
            # 화물 상하차 대기 시간 시뮬레이션
            time.sleep(2.0)
        else:
            self.get_logger().warn(f'{robot_id} failed to reach {target_zone} with status: {status}')
            self.fleet_status[robot_id]['state'] = 'IDLE'

def main(args=None):
    rclpy.init(args=args)
    fms = FmsNode()
    
    # Use MultiThreadedExecutor to handle action clients correctly
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    rclpy.spin(fms, executor=executor)
    
    fms.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
