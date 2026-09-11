# ROS2 node that turns the robot to face a detected visitor using the perception offset.

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from rclpy.node import Node
from std_msgs.msg import Bool, Float32

from lab_guide_control.pid import PID


class FacePersonNode(Node):
    def __init__(self) -> None:
        super().__init__('face_person')

        self.declare_parameter('kp', 1.2)
        self.declare_parameter('ki', 0.0)
        self.declare_parameter('kd', 0.08)
        self.declare_parameter('max_angular_speed', 1.0)
        self.declare_parameter('deadband', 0.05)
        self.declare_parameter('detection_timeout', 1.0)
        self.declare_parameter('control_rate', 20.0)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('use_stamped_cmd_vel', True)

        self._deadband = self.get_parameter('deadband').value
        self._detection_timeout = self.get_parameter('detection_timeout').value
        self._use_stamped = self.get_parameter('use_stamped_cmd_vel').value

        self._pid = PID(
            kp=self.get_parameter('kp').value,
            ki=self.get_parameter('ki').value,
            kd=self.get_parameter('kd').value,
            output_limit=self.get_parameter('max_angular_speed').value,
        )

        self._offset = 0.0
        self._last_detection_time: rclpy.time.Time | None = None
        self._estop = False
        self._enabled = False
        self._was_enabled = False

        msg_type = TwistStamped if self._use_stamped else Twist
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self._cmd_pub = self.create_publisher(msg_type, cmd_vel_topic, 10)

        self.create_subscription(Float32, '/lab_guide/person/offset', self._on_offset, 10)
        self.create_subscription(Bool, '/lab_guide/person/detected', self._on_detected, 10)
        self.create_subscription(Bool, '/lab_guide/estop', self._on_estop, 10)
        self.create_subscription(Bool, '/lab_guide/face_person/enabled', self._on_enabled, 10)

        rate = self.get_parameter('control_rate').value
        self._last_tick = self.get_clock().now()
        self.create_timer(1.0 / rate, self._tick)

        self.get_logger().info(f'face person controller ready, publishing {msg_type.__name__} on {cmd_vel_topic}')

    def _on_offset(self, msg: Float32) -> None:
        self._offset = msg.data

    def _on_detected(self, msg: Bool) -> None:
        if msg.data:
            self._last_detection_time = self.get_clock().now()

    def _on_estop(self, msg: Bool) -> None:
        if msg.data and not self._estop:
            self.get_logger().warning('emergency stop engaged, holding still')
        self._estop = msg.data

    def _on_enabled(self, msg: Bool) -> None:
        if msg.data != self._enabled:
            self.get_logger().info(f'face person behaviour {"enabled" if msg.data else "disabled"}')
        self._enabled = msg.data

    def _tick(self) -> None:
        now = self.get_clock().now()
        dt = (now - self._last_tick).nanoseconds / 1e9
        self._last_tick = now

        # While disabled, stay off the velocity topic entirely so Nav2 keeps full control of the base.
        if not self._enabled:
            if self._was_enabled:
                self._publish_angular(0.0)
                self._pid.reset()
                self._was_enabled = False
            return

        self._was_enabled = True

        if self._estop or not self._has_recent_detection(now) or dt <= 0.0:
            self._publish_angular(0.0)
            self._pid.reset()
            return

        if abs(self._offset) < self._deadband:
            self._publish_angular(0.0)
            return

        # Positive offset means the visitor sits right of centre, which needs a clockwise (negative yaw) turn.
        self._publish_angular(self._pid.update(-self._offset, dt))

    def _has_recent_detection(self, now: rclpy.time.Time) -> bool:
        if self._last_detection_time is None:
            return False
        return (now - self._last_detection_time).nanoseconds / 1e9 < self._detection_timeout

    def _publish_angular(self, angular_z: float) -> None:
        if self._use_stamped:
            msg = TwistStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'base_link'
            msg.twist.angular.z = angular_z
        else:
            msg = Twist()
            msg.angular.z = angular_z
        self._cmd_pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FacePersonNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
