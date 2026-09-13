# ROS2 node that runs the bilingual (Arabic/English) LLM agent and dispatches robot actions.

import math
import threading

import rclpy
import yaml
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, Int32, String

from lab_guide_agent.dispatcher import Dispatcher
from lab_guide_agent.llm_client import LLMError, OllamaClient, parse_tool_calls
from lab_guide_agent.tools import build_alias_index, build_tools, language_reminder, system_prompt


class AgentNode(Node):
    def __init__(self) -> None:
        super().__init__('lab_guide_agent')

        # Supplied by lab_guide_bringup, which owns the station definitions.
        self.declare_parameter('stations_file', '')
        self.declare_parameter('ollama_host', 'http://localhost:11434')
        self.declare_parameter('model', 'qwen2.5:7b')
        self.declare_parameter('temperature', 0.2)
        self.declare_parameter('max_tool_iterations', 5)
        self.declare_parameter('history_limit', 24)

        self._stations = self._load_stations(self.get_parameter('stations_file').value)
        self._aliases = build_alias_index(self._stations)
        self._max_tool_iterations = self.get_parameter('max_tool_iterations').value
        self._history_limit = self.get_parameter('history_limit').value

        self._llm = OllamaClient(
            host=self.get_parameter('ollama_host').value,
            model=self.get_parameter('model').value,
            temperature=self.get_parameter('temperature').value,
        )
        self._dispatcher = Dispatcher(build_tools(self))
        self._system_prompt = system_prompt(self.list_stations())
        self._history: list[dict] = []
        self._lock = threading.Lock()

        self._nav_state = 'idle'
        self._nav_goal_handle = None
        self._visitor_count = 0
        self._estop = False

        self._reply_pub = self.create_publisher(String, '/lab_guide/chat/out', 10)
        self._face_pub = self.create_publisher(Bool, '/lab_guide/face_person/enabled', 10)
        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        chat_group = ReentrantCallbackGroup()
        self.create_subscription(String, '/lab_guide/chat/in', self._on_chat, 10, callback_group=chat_group)
        self.create_subscription(Int32, '/lab_guide/person/count', self._on_count, 10)
        self.create_subscription(Float32, '/lab_guide/person/bearing', self._on_bearing, 10)
        self.create_subscription(Bool, '/lab_guide/estop', self._on_estop, 10)

        self._bearing = 0.0
        self.get_logger().info(f'agent ready with stations: {", ".join(self._stations)}')

    # ----- ROS callbacks -----

    def _on_count(self, msg: Int32) -> None:
        self._visitor_count = msg.data

    def _on_bearing(self, msg: Float32) -> None:
        self._bearing = msg.data

    def _on_estop(self, msg: Bool) -> None:
        if msg.data and not self._estop:
            self.get_logger().warning('emergency stop engaged, cancelling navigation')
            self._cancel_navigation()
            self._face_pub.publish(Bool(data=False))
        self._estop = msg.data

    def _on_chat(self, msg: String) -> None:
        text = msg.data.strip()
        if not text:
            return

        self.get_logger().info(f'visitor: {text}')
        with self._lock:
            self._history.append({'role': 'user', 'content': text})
            reply = self._run_agent(text)
            self._trim_history()

        self.get_logger().info(f'robot: {reply}')
        self._reply_pub.publish(String(data=reply))

    # ----- agent loop -----

    def _run_agent(self, text: str) -> str:
        # The reminder sits after the history so it is the last thing the model reads before answering.
        messages = [
            {'role': 'system', 'content': self._system_prompt},
            *self._history,
            {'role': 'system', 'content': language_reminder(text)},
        ]

        for _ in range(self._max_tool_iterations):
            try:
                message = self._llm.chat(messages, tools=self._dispatcher.specs())
            except LLMError as exc:
                self.get_logger().error(str(exc))
                return 'Sorry, my language model is not reachable right now.'

            messages.append(message)
            self._history.append(message)

            calls = parse_tool_calls(message)
            if not calls:
                return (message.get('content') or '').strip()

            for name, arguments in calls:
                result = self._dispatcher.dispatch(name, arguments)
                self.get_logger().info(f'tool {name}({arguments}) -> {result.content}')
                tool_message = {'role': 'tool', 'name': name, 'content': result.content}
                messages.append(tool_message)
                self._history.append(tool_message)

        return 'Sorry, I got stuck working that out. Could you rephrase?'

    def _trim_history(self) -> None:
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit:]

    # ----- RobotInterface, called from tool handlers -----

    def list_stations(self) -> list[str]:
        return list(self._stations)

    def describe_station(self, station: str) -> str:
        entry = self._station(station)
        return entry.get('description', f'{station} is a station in the lab.')

    def go_to_station(self, station: str) -> str:
        if self._estop:
            return 'cannot drive: the emergency stop is engaged'

        entry = self._station(station)
        if not self._nav_client.wait_for_server(timeout_sec=5.0):
            raise RuntimeError('Nav2 navigate_to_pose action server is not available')

        goal = NavigateToPose.Goal()
        goal.pose = self._pose_from(entry)
        self._nav_state = f'driving to {station}'
        self._nav_client.send_goal_async(goal).add_done_callback(
            lambda future: self._on_goal_response(future, station)
        )
        return f'navigation started towards {station}'

    def stop(self) -> str:
        self._cancel_navigation()
        self._face_pub.publish(Bool(data=False))
        return 'stopped'

    def get_status(self) -> str:
        parts = [
            f'navigation: {self._nav_state}',
            f'visitors visible: {self._visitor_count}',
            f'emergency stop: {"engaged" if self._estop else "clear"}',
        ]
        if self._visitor_count:
            side = 'right' if self._bearing > 0 else 'left'
            parts.append(f'nearest visitor is {abs(math.degrees(self._bearing)):.0f} degrees to the {side}')
        return '; '.join(parts)

    def face_visitor(self, enabled: bool) -> str:
        self._face_pub.publish(Bool(data=bool(enabled)))
        return f'visitor tracking {"enabled" if enabled else "disabled"}'

    # ----- navigation plumbing -----

    def _on_goal_response(self, future, station: str) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._nav_state = f'goal to {station} was rejected'
            self.get_logger().warning(self._nav_state)
            return

        self._nav_goal_handle = goal_handle
        goal_handle.get_result_async().add_done_callback(lambda result: self._on_goal_result(result, station))

    def _on_goal_result(self, future, station: str) -> None:
        status = future.result().status
        # 4 is STATUS_SUCCEEDED in action_msgs/GoalStatus.
        self._nav_state = f'arrived at {station}' if status == 4 else f'failed to reach {station}'
        self._nav_goal_handle = None
        self.get_logger().info(self._nav_state)

    def _cancel_navigation(self) -> None:
        if self._nav_goal_handle is not None:
            self._nav_goal_handle.cancel_goal_async()
            self._nav_goal_handle = None
        self._nav_state = 'idle'

    def _pose_from(self, entry: dict) -> PoseStamped:
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(entry['x'])
        pose.pose.position.y = float(entry['y'])
        yaw = float(entry.get('yaw', 0.0))
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose

    def _station(self, station: str) -> dict:
        name = self._aliases.get(station.strip().lower())
        if name is None:
            raise KeyError(f'unknown station {station!r}; known stations: {", ".join(self._stations)}')
        return self._stations[name]

    def _load_stations(self, path: str) -> dict[str, dict]:
        if not path:
            raise ValueError('the stations_file parameter must point at a stations YAML file')
        with open(path) as handle:
            document = yaml.safe_load(handle) or {}
        return {str(name).lower(): entry for name, entry in (document.get('stations') or {}).items()}



def main(args=None) -> None:
    rclpy.init(args=args)
    node = AgentNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
