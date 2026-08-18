#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String

class FmsNode(Node):
    def __init__(self):
        super().__init__('fms_node')
        self.get_logger().info('Initializing Fleet Management System (FMS) Node')

        # 로봇 상태 관리 딕셔너리
        self.fleet_status = {
            'tb1': {'battery': 100, 'state': 'IDLE', 'task': None},
            'tb2': {'battery': 95,  'state': 'IDLE', 'task': None},
            'tb3': {'battery': 80,  'state': 'IDLE', 'task': None},
            'tb4': {'battery': 20,  'state': 'CHARGING', 'task': None} # tb4는 예비 자원으로 가정
        }

        # 각 로봇의 목적지를 하달할 퍼블리셔 (Nav2 Goal)
        self.goal_publishers = {}
        for robot_id in self.fleet_status.keys():
            topic_name = f'/{robot_id}/goal_pose'
            self.goal_publishers[robot_id] = self.create_publisher(PoseStamped, topic_name, 10)

        # 작업 할당을 시뮬레이션하기 위한 타이머 (5초마다 실행)
        self.timer = self.create_timer(5.0, self.task_allocation_loop)

    def task_allocation_loop(self):
        # 1. 미할당 작업 확인 (시나리오 상: 적재 구역에서 A, B, C로 화물 3개 이송)
        # 2. 가용한 로봇 3대(tb1, tb2, tb3) 선정
        # 3. Nav2 Goal 퍼블리시
        # 4. 교차로 진입 시 양보 로직(트래픽 제어) 모니터링
        
        idle_robots = [r_id for r_id, status in self.fleet_status.items() if status['state'] == 'IDLE']
        if len(idle_robots) >= 3:
            self.get_logger().info(f'Allocating tasks to {idle_robots[:3]}...')
            # 실제로는 각 로봇별 적재 구역 좌표를 퍼블리시합니다.
            # 여기서는 뼈대 코드로만 남겨둡니다.
            for r_id in idle_robots[:3]:
                self.fleet_status[r_id]['state'] = 'MOVING_TO_LOAD'
        else:
            self.get_logger().debug('Waiting for available robots or tasks...')

def main(args=None):
    rclpy.init(args=args)
    fms = FmsNode()
    rclpy.spin(fms)
    fms.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
