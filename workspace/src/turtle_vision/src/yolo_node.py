#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
# import cv2
# from ultralytics import YOLO

class YoloVisionNode(Node):
    def __init__(self):
        super().__init__('yolo_vision_node')
        self.get_logger().info('Initializing YOLO Vision Node for Dynamic Obstacle Detection')
        
        # self.model = YOLO('yolov8n.pt') # 모델 로드 주석 처리 (초기 스켈레톤)
        
        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )
        self.publisher_ = self.create_publisher(Image, '/turtle_vision/yolo_result', 10)

    def image_callback(self, msg):
        # 1. ROS Image를 OpenCV 이미지로 변환 (CvBridge)
        # 2. YOLO 추론 수행 (self.model(cv_image))
        # 3. 인식된 Bounding Box 그리기
        # 4. 작업자(Person) 또는 박스(Box) 인식 시 FMS로 상태 퍼블리시
        # 5. 결과를 /turtle_vision/yolo_result 에 퍼블리시
        # self.get_logger().debug('Processing image frame...')
        pass

def main(args=None):
    rclpy.init(args=args)
    node = YoloVisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
