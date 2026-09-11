# Tool definitions the LLM agent can call to control the robot, plus the bilingual system prompt.

from typing import Protocol

from lab_guide_agent.dispatcher import Tool

SYSTEM_PROMPT = """You are the guide robot for a research lab. You speak both Arabic and English.

Always reply in the same language the visitor used. If they write in Arabic, answer in Arabic; if they
write in English, answer in English. Keep answers short and friendly, one or two sentences, because they
are spoken aloud to someone standing next to you.

Use the tools to act on the world instead of guessing. Call list_stations before naming a station you are
unsure about, and never invent a station that is not in the list. When a visitor asks to be taken
somewhere, call go_to_station and tell them you are on the way. If someone asks you to stop, call stop
immediately. Answer questions about what you can see by calling get_status rather than assuming.
"""


class RobotInterface(Protocol):
    """What the agent node must provide for the tools to drive the robot."""

    def list_stations(self) -> list[str]: ...

    def describe_station(self, station: str) -> str: ...

    def go_to_station(self, station: str) -> str: ...

    def stop(self) -> str: ...

    def get_status(self) -> str: ...

    def face_visitor(self, enabled: bool) -> str: ...


def build_tools(robot: RobotInterface) -> list[Tool]:
    return [
        Tool(
            name='list_stations',
            description='List the named stations in the lab that the robot can drive to.',
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: ', '.join(robot.list_stations()),
        ),
        Tool(
            name='describe_station',
            description='Explain what a particular lab station is used for.',
            parameters={
                'type': 'object',
                'properties': {
                    'station': {'type': 'string', 'description': 'Name of the station, as given by list_stations.'},
                },
                'required': ['station'],
            },
            handler=robot.describe_station,
        ),
        Tool(
            name='go_to_station',
            description='Drive the robot to a named station so the visitor can be shown around.',
            parameters={
                'type': 'object',
                'properties': {
                    'station': {'type': 'string', 'description': 'Name of the station, as given by list_stations.'},
                },
                'required': ['station'],
            },
            handler=robot.go_to_station,
        ),
        Tool(
            name='stop',
            description='Stop the robot immediately and cancel whatever it is currently driving towards.',
            parameters={'type': 'object', 'properties': {}},
            handler=robot.stop,
        ),
        Tool(
            name='get_status',
            description=(
                'Report what the robot is doing right now: navigation state, how many visitors it can see, '
                'and whether the emergency stop is engaged.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=robot.get_status,
        ),
        Tool(
            name='face_visitor',
            description='Turn the camera-tracking behaviour on or off, so the robot rotates to face the nearest visitor.',
            parameters={
                'type': 'object',
                'properties': {
                    'enabled': {'type': 'boolean', 'description': 'True to start facing visitors, false to stop.'},
                },
                'required': ['enabled'],
            },
            handler=robot.face_visitor,
        ),
    ]
