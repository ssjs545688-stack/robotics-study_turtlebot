#!/usr/bin/env python3
# pyrefly: ignore [missing-import]
import rclpy
# pyrefly: ignore [missing-import]
from rclpy.node import Node
# pyrefly: ignore [missing-import]
from rclpy.action import ActionClient
# pyrefly: ignore [missing-import]
from geometry_msgs.msg import PoseStamped
# pyrefly: ignore [missing-import]
from nav2_msgs.action import NavigateToPose
# pyrefly: ignore [missing-import]
from action_msgs.msg import GoalStatus  # [H-3 수정] 상태 코드 상수 임포트
# pyrefly: ignore [missing-import]
from std_msgs.msg import String
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
            'tb1': {'state': 'IDLE',     'current_target': None, 'battery': 100, 'wait_until': 0, 'start_moving_time': 0},
            'tb2': {'state': 'IDLE',     'current_target': None, 'battery': 95,  'wait_until': 0, 'start_moving_time': 0},
            'tb3': {'state': 'IDLE',     'current_target': None, 'battery': 80,  'wait_until': 0, 'start_moving_time': 0},
            # [L-3 수정] tb4: CHARGING 상태 — task_allocation_loop에서 충전 관리
            'tb4': {'state': 'CHARGING', 'current_target': None, 'battery': 20,  'wait_until': 0, 'start_moving_time': 0}
        }
        
        # [Zone Lock 추가] 점유된 구역을 관리하는 Set
        self.locked_zones = set()
        
        # 현재 임무 단계 (LOADING, UNLOADING, STANDBY)
        self.phase = 'LOADING'

        # Action Clients 생성 (Nav2)
        self.nav_clients = {}
        for robot_id in self.fleet_status.keys():
            action_topic = f'/{robot_id}/navigate_to_pose'
            client = ActionClient(self, NavigateToPose, action_topic)
            self.nav_clients[robot_id] = client

        # 작업 큐: (작업 목적지, 우선순위)
        self.pending_tasks = ['loading', 'loading', 'loading']
        self.task_destinations = ['unload_A', 'unload_B', 'unload_C']
        
        # Scenario 연동 Publisher
        self.spawn_pub = self.create_publisher(String, '/scenario/spawn_cargo', 10)
        self.despawn_pub = self.create_publisher(String, '/scenario/despawn_cargo', 10)

        # 5초마다 작업 할당 평가 루프 실행
        self.timer = self.create_timer(5.0, self.task_allocation_loop)

    def euler_to_quaternion(self, yaw):
        return [0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)]

    def create_pose_stamped(self, target_zone):
        pose = PoseStamped()
        # 글로벌 map 프레임을 기준 프레임으로 사용
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        coords = ZONES[target_zone]
        
        # 월드 좌표(ZONES)를 차감 없이 그대로 사용
        pose.pose.position.x = float(coords['x'])
        pose.pose.position.y = float(coords['y'])
        
        q = self.euler_to_quaternion(coords['yaw'])
        pose.pose.orientation.x = q[0]
        pose.pose.orientation.y = q[1]
        pose.pose.orientation.z = q[2]
        pose.pose.orientation.w = q[3]
        return pose

    def task_allocation_loop(self):
        # [L-3 수정] CHARGING 상태: 5초 타이머마다 5% 충전, 50% 이상이면 IDLE 전환
        for robot_id, status in self.fleet_status.items():
            if status['state'] == 'CHARGING':
                status['battery'] = min(100, status['battery'] + 5)
                self.get_logger().info(f'[CHARGING] {robot_id} battery: {status["battery"]}%')
                if status['battery'] >= 50:
                    status['state'] = 'IDLE'
                    self.get_logger().info(f'{robot_id} 충전 완료 ({status["battery"]}%). IDLE 상태로 전환.')

        # [C-3 수정] WAITING 상태: ROS 클럭 기반으로 하역 대기 시간 체크 (time.sleep 미사용)
        now_ns = self.get_clock().now().nanoseconds
        for robot_id, status in self.fleet_status.items():
            if status['state'] == 'WAITING' and now_ns >= status.get('wait_until', 0):
                status['state'] = 'IDLE'
                self.get_logger().info(f'{robot_id} 하역 완료. IDLE 상태로 전환.')

        # [Deadlock 감지 추가] MOVING 상태인데 60초 이상 도달하지 못한 로봇 감지
        for robot_id, status in self.fleet_status.items():
            if status['state'] == 'MOVING':
                start_time = status.get('start_moving_time', 0)
                if start_time > 0 and (now_ns - start_time) > 60_000_000_000:  # 60초 초과
                    target_zone = status.get('current_target', 'unknown')
                    self.get_logger().warn(f'[Deadlock 감지] {robot_id}가 {target_zone}으로 이동 중 멈췄습니다!')

        idle_robots = [r for r, status in self.fleet_status.items() if status['state'] == 'IDLE']
        
        any_active_robot = any(status['state'] in ['MOVING', 'WAITING'] for status in self.fleet_status.values())
        
        if not self.pending_tasks and not any_active_robot:
            if self.phase == 'LOADING' and self.task_destinations:
                self.pending_tasks = list(self.task_destinations)
                self.task_destinations = []
                self.phase = 'UNLOADING'
                self.get_logger().info('Switching phase: Moving to Unload Zones')
            elif self.phase == 'UNLOADING':
                self.get_logger().info('All tasks completed. Returning to standby.')
                self.pending_tasks = ['standby', 'standby', 'standby', 'standby']
                self.phase = 'STANDBY'
            elif self.phase == 'STANDBY':
                pass

        for robot_id in idle_robots:
            if not self.pending_tasks:
                break
                
            # [Zone Lock 추가] 잠겨있지 않은 목적지를 찾아서 할당
            assigned_zone = None
            for i, zone in enumerate(self.pending_tasks):
                if zone not in self.locked_zones:
                    assigned_zone = self.pending_tasks.pop(i)
                    break
                    
            if assigned_zone is None:
                # 할당 가능한 작업의 목적지가 모두 Lock 상태임 (대기)
                continue
                
            target_zone = assigned_zone
            self.locked_zones.add(target_zone)  # [Zone Lock 추가] 구역 Lock 설정
            
            self.get_logger().info(f'Allocating task to {robot_id}: Go to [{target_zone}]')
            
            # 상태 업데이트
            self.fleet_status[robot_id]['state'] = 'MOVING'
            self.fleet_status[robot_id]['current_target'] = target_zone
            self.fleet_status[robot_id]['start_moving_time'] = self.get_clock().now().nanoseconds  # [Deadlock 감지 추가]
            
            # Nav2 Goal 전송
            self.send_nav_goal(robot_id, target_zone)

    def send_nav_goal(self, robot_id, target_zone):
        client = self.nav_clients[robot_id]
        if not client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error(f'Nav2 Action server not available for {robot_id}')
            self.fleet_status[robot_id]['state'] = 'IDLE'  # 롤백
            self.pending_tasks.insert(0, target_zone)
            self.locked_zones.discard(target_zone)  # [Zone Lock 추가] Lock 해제
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
            self.pending_tasks.insert(0, target_zone)
            self.locked_zones.discard(target_zone)  # [Zone Lock 추가] Lock 해제
            return

        self.get_logger().info(f'Goal accepted for {robot_id}')
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(lambda future: self.get_result_cb(future, robot_id, target_zone))

    def feedback_cb(self, robot_id, feedback_msg):
        # 거리 등 상태 모니터링 가능
        pass

    def get_result_cb(self, future, robot_id, target_zone):
        result = future.result().result  # noqa: F841
        status = future.result().status
        
        # [Zone Lock 추가] 목적지 도착 또는 실패 시 Lock 해제
        self.locked_zones.discard(target_zone)
        
        # [H-3 수정] 하드코딩된 '4' → GoalStatus 상수 사용
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'{robot_id} arrived at {target_zone} successfully!')
            self.fleet_status[robot_id]['state'] = 'IDLE'
            self.fleet_status[robot_id]['current_target'] = None
            
            # [C-3 수정] time.sleep(2.0) 제거 → WAITING 상태 + ROS 클럭 기반 타이머
            # 2초 후 IDLE 전환 (task_allocation_loop에서 처리)
            self.fleet_status[robot_id]['state'] = 'WAITING'
            wait_until_ns = self.get_clock().now().nanoseconds + 2_000_000_000  # 2초
            self.fleet_status[robot_id]['wait_until'] = wait_until_ns
            
            # Scenario Manager 연동: Spawn / Despawn 트리거
            if target_zone == 'loading':
                msg = String()
                coords = ZONES[target_zone]
                msg.data = f"{robot_id},{coords['x']},{coords['y']}"
                self.spawn_pub.publish(msg)
            elif target_zone.startswith('unload'):
                msg = String()
                msg.data = robot_id
                self.despawn_pub.publish(msg)
        else:
            self.get_logger().warn(f'{robot_id} failed to reach {target_zone} with status: {status}')
            self.fleet_status[robot_id]['state'] = 'IDLE'
            self.pending_tasks.insert(0, target_zone)

def main(args=None):
    rclpy.init(args=args)
    fms = FmsNode()
    
    # Use MultiThreadedExecutor to handle action clients correctly
    # pyrefly: ignore [missing-import]
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    rclpy.spin(fms, executor=executor)
    
    fms.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
