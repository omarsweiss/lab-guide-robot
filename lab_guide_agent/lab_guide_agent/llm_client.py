# Client wrapper for calling the local Ollama LLM backend with tool-calling support.

from typing import Any

import requests

DEFAULT_HOST = 'http://localhost:11434'
# qwen2.5 is the default because its Arabic is far stronger than llama3.1's, which matters for a bilingual guide.
DEFAULT_MODEL = 'qwen2.5:7b'


class LLMError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.2,
        timeout: float = 300.0,
    ) -> None:
        self.host = host.rstrip('/')
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send the conversation to Ollama and return the assistant message, which may carry tool calls."""
        payload: dict[str, Any] = {
            'model': self.model,
            'messages': messages,
            'stream': False,
            'options': {'temperature': self.temperature},
        }
        if tools:
            payload['tools'] = tools

        try:
            response = requests.post(f'{self.host}/api/chat', json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise LLMError(f'could not reach Ollama at {self.host}: {exc}') from exc

        message = response.json().get('message')
        if message is None:
            raise LLMError('Ollama response did not contain a message')
        return message


def parse_tool_calls(message: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Extract (name, arguments) pairs from an assistant message."""
    calls = []
    for call in message.get('tool_calls') or []:
        function = call.get('function', {})
        name = function.get('name')
        if not name:
            continue
        arguments = function.get('arguments') or {}
        calls.append((name, arguments))
    return calls
