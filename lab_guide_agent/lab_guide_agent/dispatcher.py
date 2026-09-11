# Routes tool calls emitted by the LLM to the registered robot handlers.

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., str]

    @property
    def required(self) -> list[str]:
        return list(self.parameters.get('required', []))


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    content: str


class Dispatcher:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f'tool already registered: {tool.name}')
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def specs(self) -> list[dict[str, Any]]:
        """Tool schemas in the OpenAI/Ollama function-calling format."""
        return [
            {
                'type': 'function',
                'function': {
                    'name': tool.name,
                    'description': tool.description,
                    'parameters': tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def dispatch(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        """Run a tool call. Failures come back as results, not exceptions, so the model can see and recover from them."""
        arguments = arguments or {}

        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(False, f'unknown tool {name!r}; available tools: {", ".join(self.names())}')

        missing = [key for key in tool.required if key not in arguments]
        if missing:
            return ToolResult(False, f'tool {name!r} is missing required argument(s): {", ".join(missing)}')

        allowed = set(tool.parameters.get('properties', {}))
        unexpected = [key for key in arguments if key not in allowed]
        if unexpected:
            return ToolResult(False, f'tool {name!r} got unexpected argument(s): {", ".join(unexpected)}')

        try:
            return ToolResult(True, str(tool.handler(**arguments)))
        except Exception as exc:  # noqa: BLE001 - surfaced to the model as a recoverable tool failure
            return ToolResult(False, f'tool {name!r} failed: {exc}')
