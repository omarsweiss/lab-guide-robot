# ROS2 node that runs YOLO person detection on the camera feed and publishes visitor detections.

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32, Int32
from ultralytics import YOLO

from lab_guide_perception.offset import BoundingBox, bearing, largest, normalized_offset

PERSON_CLASS_ID = 0


class PersonDetectorNode(Node):
    def __init__(self) -> None:
        super().__init__('person_detector')

        self.declare_parameter('camera_topic', '/camera/image_raw')
        self.declare_parameter('model', 'yolov8n.pt')
        self.declare_parameter('confidence', 0.5)
        self.declare_parameter('horizontal_fov', 1.396)  # TurtleBot3 Waffle camera, ~80 degrees.
        self.declare_parameter('publish_debug_image', True)
        self.declare_parameter('device', 'cpu')

        camera_topic = self.get_parameter('camera_topic').value
        self._confidence = self.get_parameter('confidence').value
        self._horizontal_fov = self.get_parameter('horizontal_fov').value
        self._publish_debug = self.get_parameter('publish_debug_image').value

        self._bridge = CvBridge()
        self._model = YOLO(self.get_parameter('model').value)
        self._device = self.get_parameter('device').value

        self._detected_pub = self.create_publisher(Bool, '/lab_guide/person/detected', 10)
        self._count_pub = self.create_publisher(Int32, '/lab_guide/person/count', 10)
        self._offset_pub = self.create_publisher(Float32, '/lab_guide/person/offset', 10)
        self._bearing_pub = self.create_publisher(Float32, '/lab_guide/person/bearing', 10)
        self._debug_pub = self.create_publisher(Image, '/lab_guide/person/debug_image', 10)

        self.create_subscription(Image, camera_topic, self._on_image, qos_profile_sensor_data)
        self.get_logger().info(f'person detector ready, watching {camera_topic}')

    def _on_image(self, msg: Image) -> None:
        frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        boxes = self._detect_people(frame)

        self._count_pub.publish(Int32(data=len(boxes)))
        self._detected_pub.publish(Bool(data=bool(boxes)))

        target = largest(boxes)
        if target is not None:
            width = frame.shape[1]
            self._offset_pub.publish(Float32(data=normalized_offset(target, width)))
            self._bearing_pub.publish(Float32(data=bearing(target, width, self._horizontal_fov)))

        if self._publish_debug:
            self._publish_debug_image(frame, boxes, target, msg.header)

    def _detect_people(self, frame) -> list[BoundingBox]:
        results = self._model.predict(
            frame,
            classes=[PERSON_CLASS_ID],
            conf=self._confidence,
            device=self._device,
            verbose=False,
        )

        boxes = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                boxes.append(BoundingBox(x1, y1, x2, y2, confidence=float(box.conf[0])))
        return boxes

    def _publish_debug_image(self, frame, boxes, target, header) -> None:
        annotated = frame.copy()
        for box in boxes:
            color = (0, 255, 0) if box is target else (255, 160, 0)
            cv2.rectangle(annotated, (int(box.x1), int(box.y1)), (int(box.x2), int(box.y2)), color, 2)
            cv2.putText(
                annotated,
                f'person {box.confidence:.2f}',
                (int(box.x1), max(int(box.y1) - 8, 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

        debug_msg = self._bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        debug_msg.header = header
        self._debug_pub.publish(debug_msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PersonDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
