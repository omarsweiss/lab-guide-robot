# Unit tests for dispatcher.py.

import pytest

from lab_guide_agent.dispatcher import Dispatcher, Tool
from lab_guide_agent.tools import build_alias_index, is_arabic, language_reminder, system_prompt


def make_tool(handler, *, name='go_to_station', required=('station',)):
    return Tool(
        name=name,
        description='Drive to a named station.',
        parameters={
            'type': 'object',
            'properties': {'station': {'type': 'string'}},
            'required': list(required),
        },
        handler=handler,
    )


def test_dispatch_calls_the_handler_and_returns_its_output():
    dispatcher = Dispatcher([make_tool(lambda station: f'heading to {station}')])
    result = dispatcher.dispatch('go_to_station', {'station': 'microscope'})
    assert result.ok
    assert result.content == 'heading to microscope'


def test_handler_output_is_coerced_to_text_for_the_model():
    tool = Tool(name='count_visitors', description='', parameters={'type': 'object', 'properties': {}}, handler=lambda: 3)
    result = Dispatcher([tool]).dispatch('count_visitors')
    assert result.ok
    assert result.content == '3'


def test_unknown_tool_is_reported_rather_than_raised():
    dispatcher = Dispatcher([make_tool(lambda station: station)])
    result = dispatcher.dispatch('teleport', {'station': 'moon'})
    assert not result.ok
    assert 'unknown tool' in result.content
    assert 'go_to_station' in result.content


def test_missing_required_argument_is_reported():
    dispatcher = Dispatcher([make_tool(lambda station: station)])
    result = dispatcher.dispatch('go_to_station', {})
    assert not result.ok
    assert 'station' in result.content


def test_unexpected_argument_is_reported():
    dispatcher = Dispatcher([make_tool(lambda station: station)])
    result = dispatcher.dispatch('go_to_station', {'station': 'desk', 'speed': 9000})
    assert not result.ok
    assert 'speed' in result.content


def test_handler_failure_becomes_a_failed_result():
    def explode(station):
        raise RuntimeError('nav2 server unavailable')

    result = Dispatcher([make_tool(explode)]).dispatch('go_to_station', {'station': 'desk'})
    assert not result.ok
    assert 'nav2 server unavailable' in result.content


def test_registering_a_duplicate_tool_is_rejected():
    dispatcher = Dispatcher([make_tool(lambda station: station)])
    with pytest.raises(ValueError):
        dispatcher.register(make_tool(lambda station: station))


def test_specs_use_the_function_calling_schema():
    dispatcher = Dispatcher([make_tool(lambda station: station)])
    (spec,) = dispatcher.specs()
    assert spec['type'] == 'function'
    assert spec['function']['name'] == 'go_to_station'
    assert spec['function']['parameters']['required'] == ['station']


def test_names_are_sorted():
    tools = [
        make_tool(lambda: 'a', name='stop', required=()),
        make_tool(lambda: 'b', name='face_person', required=()),
    ]
    assert Dispatcher(tools).names() == ['face_person', 'stop']


# ----- station aliases and language handling -----

STATIONS = {
    'microscope': {'aliases': ['المجهر', 'ميكروسكوب', 'the microscope']},
    'printer_3d': {'aliases': ['3d printer', 'الطابعة']},
    'entrance': {},
}


def test_canonical_names_resolve_to_themselves():
    index = build_alias_index(STATIONS)
    assert index['microscope'] == 'microscope'
    assert index['entrance'] == 'entrance'


def test_arabic_alias_resolves_to_the_canonical_station():
    index = build_alias_index(STATIONS)
    assert index['المجهر'] == 'microscope'
    assert index['ميكروسكوب'] == 'microscope'
    assert index['الطابعة'] == 'printer_3d'


def test_aliases_are_matched_case_and_space_insensitively():
    index = build_alias_index(STATIONS)
    assert index['  The Microscope '.strip().lower()] == 'microscope'
    assert index['3D Printer'.strip().lower()] == 'printer_3d'


def test_station_without_aliases_still_resolves():
    assert build_alias_index({'entrance': {}})['entrance'] == 'entrance'


def test_arabic_script_is_detected():
    assert is_arabic('من فضلك خذني إلى المجهر')
    assert not is_arabic('take me to the microscope')
    assert not is_arabic('printer_3d')


def test_language_reminder_names_the_visitors_language():
    assert 'Arabic' in language_reminder('ما هي الأماكن؟')
    assert 'English' in language_reminder('what places are there?')


def test_system_prompt_lists_the_real_stations():
    prompt = system_prompt(['entrance', 'microscope'])
    assert 'entrance, microscope' in prompt
    assert 'Arabic' in prompt and 'English' in prompt
