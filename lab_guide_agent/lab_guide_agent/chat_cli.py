# Command-line chat interface for talking to the lab-guide agent in Arabic or English.

import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ChatCli(Node):
    def __init__(self) -> None:
        super().__init__('chat_cli')
        self._pub = self.create_publisher(String, '/lab_guide/chat/in', 10)
        self.create_subscription(String, '/lab_guide/chat/out', self._on_reply, 10)

    def _on_reply(self, msg: String) -> None:
        print(f'\nrobot: {msg.data}\nyou> ', end='', flush=True)

    def send(self, text: str) -> None:
        self._pub.publish(String(data=text))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ChatCli()

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    print('Talk to the lab guide robot in Arabic or English. Ctrl-D to quit.')
    try:
        while True:
            text = input('you> ').strip()
            if text:
                node.send(text)
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
