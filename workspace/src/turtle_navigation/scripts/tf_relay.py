#!/usr/bin/env python3
"""
tf_relay.py — 네임스페이스 TF 중계 노드
=========================================
spawn_turtlebots.launch.py 가 /{ns}/tf 로 퍼블리시하는 TF를
slam_toolbox 가 읽을 수 있도록 글로벌 /tf 와 /tf_static 으로 중계합니다.

[핵심 수정 사항]
  /tf_static 은 Transient Local QoS 를 사용합니다.
  일반 구독(Volatile)으로는 노드 시작 전에 이미 발행된 정적 TF 메시지를
  늦게 참여해도 받을 수 없습니다 (late-join 불가).
  Transient Local QoS로 구독해야 캐시된 초기 메시지를 즉시 수신합니다.

사용법 (mapping.launch.py 에서 자동 실행됨):
  ros2 run turtle_navigation tf_relay.py --ros-args -p namespace:=tb1
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy, QoSHistoryPolicy
# pyrefly: ignore [missing-import]
from tf2_msgs.msg import TFMessage


# /tf_static 전용 QoS: Transient Local (late-join 시에도 캐시 메시지 수신 가능)
STATIC_TF_QOS = QoSProfile(
    depth=100,
    durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
    reliability=QoSReliabilityPolicy.RELIABLE,
    history=QoSHistoryPolicy.KEEP_LAST,
)

# /tf 전용 QoS: 일반 Volatile
TF_QOS = QoSProfile(
    depth=100,
    durability=QoSDurabilityPolicy.VOLATILE,
    reliability=QoSReliabilityPolicy.RELIABLE,
    history=QoSHistoryPolicy.KEEP_LAST,
)


class TfRelay(Node):
    def __init__(self):
        super().__init__('tf_relay')

        self.declare_parameter('namespace', 'tb1')
        ns = self.get_parameter('namespace').get_parameter_value().string_value

        self.get_logger().info(
            f'TF Relay 시작: /{ns}/tf → /tf (Volatile), '
            f'/{ns}/tf_static → /tf_static (Transient Local)'
        )

        # ── 퍼블리셔 ─────────────────────────────────────────────────
        # /tf: Volatile QoS
        self.tf_pub = self.create_publisher(TFMessage, '/tf', TF_QOS)
        # /tf_static: Transient Local QoS (slam_toolbox, rviz가 기대하는 QoS)
        self.tf_static_pub = self.create_publisher(TFMessage, '/tf_static', STATIC_TF_QOS)

        # ── 구독자 ─────────────────────────────────────────────────
        # /{ns}/tf: Volatile
        self.create_subscription(TFMessage, f'/{ns}/tf', self.tf_cb, TF_QOS)
        # /{ns}/tf_static: Transient Local (초기 발행 메시지도 놓치지 않도록)
        self.create_subscription(TFMessage, f'/{ns}/tf_static', self.tf_static_cb, STATIC_TF_QOS)

        self.get_logger().info('TF Relay 구독 준비 완료.')

    def tf_cb(self, msg: TFMessage):
        self.tf_pub.publish(msg)

    def tf_static_cb(self, msg: TFMessage):
        self.tf_static_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TfRelay()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
