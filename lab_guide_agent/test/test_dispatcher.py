# Unit tests for dispatcher.py.

import pytest

from lab_guide_agent.dispatcher import Dispatcher, Tool


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
