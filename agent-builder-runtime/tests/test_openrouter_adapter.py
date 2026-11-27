"""OpenRouter 구현 — 요청·응답 맞바꾸기와 실패 해석.

가짜 연결점으로, 네트워크 없이 돈다.
"""

import base64
import json
from decimal import Decimal

import pytest

from agent_builder_core.contracts.model import (
    ModelCallFailed,
    ModelProvider,
    ModelRequest,
    ModelSpec,
    UnknownProvider,
)
from agent_builder_infra.clients import OpenRouterCallError
from agent_builder_runtime.model_adapters import (
    OpenRouterAdapter,
    ProviderConnection,
)
from agent_builder_runtime.model_adapters.openrouter import kind_for_status
from agent_builder_runtime.repositories import MissingApiKey

PNG = base64.b64encode(b"\x89PNG....").decode()
PDF = base64.b64encode(b"%PDF-1.7").decode()

SPEC = ModelSpec(
    name="fast",
    provider="openrouter",
    provider_model="vendor/model-a",
    input_kinds=("text", "image", "file"),
)


class FakeConnection:
    def __init__(self, body=None, error: OpenRouterCallError | None = None) -> None:
        self.payloads: list[dict] = []
        self.timeouts: list[float] = []
        self._body = body
        self._error = error

    def chat(self, payload: dict, timeout_seconds: float) -> dict:
        self.payloads.append(payload)
        self.timeouts.append(timeout_seconds)
        if self._error is not None:
            raise self._error
        return self._body


def body(message=None, finish_reason="stop", **changes) -> dict:
    values = {
        "model": "vendor/model-a",
        "choices": [
            {
                "message": message or {"role": "assistant", "content": "답"},
                "finish_reason": finish_reason,
                "native_finish_reason": "end_turn",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3, "cost": 0.000012},
    }
    return {**values, **changes}


def request(**changes) -> ModelRequest:
    values = {
        "model": "fast",
        "messages": [{"role": "user", "content": "안녕"}],
        "params": {"max_output_tokens": 100},
    }
    return ModelRequest.model_validate({**values, **changes})


class FakeConnections:
    """공급자 프로필의 기본 대기 시간 30초로 연결을 내준다."""

    def __init__(self, connection, error: Exception | None = None) -> None:
        self._connection = connection
        self._error = error
        self.asked: list[str] = []

    def get(self, name: str) -> ProviderConnection:
        self.asked.append(name)
        if self._error is not None:
            raise self._error
        return ProviderConnection(self._connection, timeout_seconds=30)


def run(req: ModelRequest, connection: FakeConnection, spec: ModelSpec = SPEC):
    return OpenRouterAdapter(FakeConnections(connection)).complete(req, spec)


def test_fills_contract():
    assert isinstance(
        OpenRouterAdapter(FakeConnections(FakeConnection())), ModelProvider
    )


def test_uses_profile_timeout_unless_model_overrides():
    connection = FakeConnection(body())

    run(request(), connection)
    run(request(), connection, SPEC.model_copy(update={"timeout_seconds": 120}))

    assert connection.timeouts == [30, 120]


def test_asks_for_its_own_provider_name():
    connections = FakeConnections(FakeConnection(body()))

    OpenRouterAdapter(connections).complete(request(), SPEC)

    assert connections.asked == ["openrouter"]


def test_missing_api_key_is_auth_failure():
    req = request()
    connections = FakeConnections(None, error=MissingApiKey("키 없음"))

    with pytest.raises(ModelCallFailed) as raised:
        OpenRouterAdapter(connections).complete(req, SPEC)

    assert raised.value.kind == "auth"
    assert raised.value.retryable is False


def test_unknown_or_disabled_provider_passes_through():
    connections = FakeConnections(None, error=UnknownProvider("꺼 둔 공급자"))

    with pytest.raises(UnknownProvider):
        OpenRouterAdapter(connections).complete(request(), SPEC)


# --- 요청 ---


def test_minimal_payload():
    chat = FakeConnection(body())

    run(request(), chat)

    assert chat.payloads[0] == {
        "model": "vendor/model-a",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "안녕"}]}],
        "max_tokens": 100,
    }


def test_full_payload():
    chat = FakeConnection(body())
    req = request(
        system="짧게",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "봐"},
                    {
                        "type": "image",
                        "source": {"type": "inline", "data": PNG},
                        "media_type": "image/png",
                    },
                    {
                        "type": "image",
                        "source": {"type": "url", "url": "https://x.dev/a.png"},
                        "media_type": "image/png",
                    },
                    {
                        "type": "file",
                        "source": {"type": "inline", "data": PDF},
                        "media_type": "application/pdf",
                        "filename": "a.pdf",
                    },
                ],
            },
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "c1", "name": "search", "arguments": {"q": "한글"}}
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "결과"},
        ],
        params={
            "max_output_tokens": 50,
            "temperature": 0.2,
            "top_p": 0.9,
            "seed": 7,
            "stop": ["끝"],
        },
        tools=[
            {"name": "search", "description": "찾기", "parameters": {"type": "object"}}
        ],
        tool_choice="search",
        output={"name": "answer", "json_schema": {"type": "object"}},
    )

    run(req, chat)
    payload = chat.payloads[0]

    assert payload["messages"][0] == {"role": "system", "content": "짧게"}
    user_parts = payload["messages"][1]["content"]
    assert user_parts[1] == {
        "type": "image_url",
        "image_url": {"url": f"data:image/png;base64,{PNG}"},
    }
    assert user_parts[2] == {
        "type": "image_url",
        "image_url": {"url": "https://x.dev/a.png"},
    }
    assert user_parts[3] == {
        "type": "file",
        "file": {
            "filename": "a.pdf",
            "file_data": f"data:application/pdf;base64,{PDF}",
        },
    }
    assistant = payload["messages"][2]
    assert assistant["content"] is None
    assert json.loads(assistant["tool_calls"][0]["function"]["arguments"]) == {
        "q": "한글"
    }
    assert payload["messages"][3] == {
        "role": "tool",
        "tool_call_id": "c1",
        "content": "결과",
    }
    assert payload["tool_choice"] == {
        "type": "function",
        "function": {"name": "search"},
    }
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert (
        payload["temperature"],
        payload["top_p"],
        payload["seed"],
        payload["stop"],
    ) == (0.2, 0.9, 7, ["끝"])


def test_file_by_url_is_refused_before_sending():
    chat = FakeConnection(body())
    req = request(
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "file",
                        "source": {"type": "url", "url": "https://x.dev/a.pdf"},
                        "media_type": "application/pdf",
                    }
                ],
            }
        ]
    )

    with pytest.raises(ModelCallFailed) as raised:
        run(req, chat)

    assert raised.value.kind == "invalid_request"
    assert chat.payloads == []


# --- 응답 ---


def test_response_mapping():
    req = request()

    response = run(req, FakeConnection(body(model="vendor/model-b")))

    assert response.request_id == req.request_id
    assert response.model == "fast"
    assert response.provider == "openrouter"
    assert response.provider_model == "vendor/model-b"
    assert response.text() == "답"
    assert response.finish_reason == "stop"
    assert response.finish_detail == "end_turn"
    assert response.usage.input_tokens == 12
    assert response.usage.output_tokens == 3
    assert response.usage.cost == Decimal("0.000012")
    assert response.latency_ms >= 0


def test_tool_call_response():
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "c1",
                "type": "function",
                "function": {"name": "search", "arguments": '{"q": "x"}'},
            }
        ],
    }

    response = run(request(), FakeConnection(body(message, finish_reason="tool_calls")))

    assert response.finish_reason == "tool_calls"
    assert response.message.tool_calls[0].arguments == {"q": "x"}
    assert response.text() == ""


@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        ("length", "length"),
        ("content_filter", "content_filter"),
        (None, "other"),
        ("weird", "other"),
        ("tool_calls", "other"),
    ],
)
def test_finish_reason_mapping(reported, expected):
    # tool_calls 라고 하고 호출을 안 붙인 경우는 other 로.
    response = run(request(), FakeConnection(body(finish_reason=reported)))

    assert response.finish_reason == expected


def test_missing_cost_is_none():
    response = run(
        request(),
        FakeConnection(body(usage={"prompt_tokens": 1, "completion_tokens": 1})),
    )

    assert response.usage.cost is None


# --- 실패 ---


@pytest.mark.parametrize(
    ("error", "kind", "retryable"),
    [
        (OpenRouterCallError("timeout", "느림"), "timeout", True),
        (OpenRouterCallError("connection", "못 붙음"), "unavailable", True),
        (OpenRouterCallError("http", "x", status_code=429), "rate_limited", True),
        (OpenRouterCallError("http", "x", status_code=502), "unavailable", True),
        (OpenRouterCallError("http", "x", status_code=401), "auth", False),
        (OpenRouterCallError("http", "x", status_code=400), "invalid_request", False),
        (OpenRouterCallError("http", "x", status_code=402), "unknown", False),
    ],
)
def test_call_error_becomes_model_call_failed(error, kind, retryable):
    req = request()

    with pytest.raises(ModelCallFailed) as raised:
        run(req, FakeConnection(error=error))

    assert raised.value.kind == kind
    assert raised.value.retryable is retryable
    assert raised.value.request_id == req.request_id


@pytest.mark.parametrize(
    ("status", "kind"),
    [
        (400, "invalid_request"),
        (401, "auth"),
        (402, "unknown"),
        (403, "invalid_request"),
        (404, "invalid_request"),
        (408, "timeout"),
        (413, "invalid_request"),
        (422, "invalid_request"),
        (429, "rate_limited"),
        (500, "unavailable"),
        (503, "unavailable"),
        (418, "unknown"),
        (None, "unknown"),
    ],
)
def test_kind_for_status(status, kind):
    assert kind_for_status(status) == kind


def test_error_only_body_with_200_is_failure():
    chat = FakeConnection({"error": {"code": 503, "message": "공급자 없음"}})

    with pytest.raises(ModelCallFailed) as raised:
        run(request(), chat)

    assert raised.value.kind == "unavailable"


def test_error_inside_choice_is_failure():
    failing = body(finish_reason="error")
    failing["choices"][0]["error"] = {"code": 502, "message": "중간에 끊김"}

    with pytest.raises(ModelCallFailed) as raised:
        run(request(), FakeConnection(failing))

    assert raised.value.kind == "unavailable"
    assert "끊김" in raised.value.detail


def test_tool_arguments_not_json_is_failure():
    message = {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "c1",
                "type": "function",
                "function": {"name": "search", "arguments": "{not json"},
            }
        ],
    }

    with pytest.raises(ModelCallFailed, match="JSON"):
        run(request(), FakeConnection(body(message, finish_reason="tool_calls")))
