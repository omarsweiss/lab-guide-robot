# ROS2 node bridging serial communication with the ESP32-S3 tracking/e-stop firmware.

import serial
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32

# Mirrors firmware/esp32_pid/src/protocol.h.
CMD_TARGET = 'TGT'
CMD_GAINS = 'PID'
CMD_PING = 'PING'
MSG_STATUS = 'STS'
MSG_ESTOP = 'EST'
MSG_LOG = 'LOG'


class Esp32BridgeNode(Node):
    def __init__(self) -> None:
        super().__init__('esp32_bridge')

        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('send_rate', 20.0)
        self.declare_parameter('simulate', False)

        self._simulate = self.get_parameter('simulate').value
        self._offset = 0.0
        self._buffer = b''
        self._serial: serial.Serial | None = None

        self._estop_pub = self.create_publisher(Bool, '/lab_guide/estop', 10)
        self._angle_pub = self.create_publisher(Float32, '/lab_guide/esp32/servo_angle', 10)
        self.create_subscription(Float32, '/lab_guide/person/offset', self._on_offset, 10)

        if self._simulate:
            self.get_logger().warning('running in simulate mode, no ESP32 serial link')
        else:
            self._open_serial()

        rate = self.get_parameter('send_rate').value
        self.create_timer(1.0 / rate, self._tick)

    def _open_serial(self) -> None:
        port = self.get_parameter('port').value
        baud = self.get_parameter('baud').value
        self._serial = serial.Serial(port, baud, timeout=0)
        self.get_logger().info(f'connected to ESP32 on {port} at {baud} baud')

    def _on_offset(self, msg: Float32) -> None:
        self._offset = msg.data

    def _tick(self) -> None:
        if self._simulate:
            self._estop_pub.publish(Bool(data=False))
            self._angle_pub.publish(Float32(data=0.0))
            return

        self._write(f'{CMD_TARGET} {self._offset:.4f}')
        for line in self._read_lines():
            self._handle_line(line)

    def _write(self, line: str) -> None:
        self._serial.write(f'{line}\n'.encode())

    def _read_lines(self) -> list[str]:
        self._buffer += self._serial.read(self._serial.in_waiting or 0)
        *complete, self._buffer = self._buffer.split(b'\n')
        return [line.decode(errors='replace').strip() for line in complete]

    def _handle_line(self, line: str) -> None:
        if not line:
            return

        kind, _, payload = line.partition(' ')
        if kind == MSG_ESTOP:
            engaged = payload.strip() == '1'
            self._estop_pub.publish(Bool(data=engaged))
            if engaged:
                self.get_logger().warning('ESP32 reported emergency stop')
        elif kind == MSG_STATUS:
            angle, _, _output = payload.partition(' ')
            self._angle_pub.publish(Float32(data=float(angle)))
        elif kind == MSG_LOG:
            self.get_logger().info(f'esp32: {payload}')
        else:
            self.get_logger().debug(f'unrecognised line from esp32: {line!r}')

    def destroy_node(self) -> bool:
        if self._serial is not None:
            self._serial.close()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Esp32BridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
