# Tool definitions the LLM agent can call to control the robot, plus the bilingual system prompt.

from typing import Protocol

from lab_guide_agent.dispatcher import Tool

SYSTEM_PROMPT_TEMPLATE = """You are the guide robot for a research lab. You speak both Arabic and English.

LANGUAGE RULE. Reply in the same language the visitor wrote in. If their message is in English, your
reply must be in English. If their message is in Arabic, your reply must be in Arabic. Never switch to
the other language on your own. Keep replies to one or two short, friendly sentences, because they are
spoken aloud to someone standing next to you.

STATION NAMES. Station names are fixed identifiers, always lowercase English: {stations}.
Pass them to tools exactly as spelled, even when you are talking
to the visitor in Arabic. Never translate a station name into Arabic inside a tool call, and never invent
one that list_stations did not return. In your spoken reply you may of course name the place in Arabic.

TOOLS. Actually call the tools; never claim you did something without calling the matching tool. To take
someone somewhere, call go_to_station. To answer what places exist, call list_stations. To answer what
you can see or what you are doing, call get_status. If anyone asks you to stop, call stop immediately.
If a tool reports an error, tell the visitor plainly what went wrong instead of pretending it worked.
"""


def system_prompt(stations: list[str]) -> str:
    """The prompt names the real stations, so the model has no reason to invent or translate one."""
    return SYSTEM_PROMPT_TEMPLATE.format(stations=', '.join(stations))


def build_alias_index(stations: dict[str, dict]) -> dict[str, str]:
    """Maps every accepted spelling, including the Arabic ones, onto its canonical station name."""
    lookup = {}
    for name, entry in stations.items():
        for alias in [name, *(entry.get('aliases') or [])]:
            lookup[str(alias).strip().lower()] = name
    return lookup


def is_arabic(text: str) -> bool:
    """True when the text contains Arabic script."""
    return any('؀' <= char <= 'ۿ' or 'ݐ' <= char <= 'ݿ' for char in text)


def language_reminder(text: str) -> str:
    """Small models drift out of the visitor's language, so the choice is made here and stated outright."""
    language = 'Arabic' if is_arabic(text) else 'English'
    return f'The visitor wrote in {language}. Write your reply in {language} and no other language.'


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
