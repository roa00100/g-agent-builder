"""모델 응답 계약. 공급자 없이 모양과 규칙을 확인한다."""

from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from agent_builder_core.contracts.model import (
    Message,
    ModelCallFailed,
    ModelRequest,
    ModelResponse,
    parse_output,
)


def response(**changes) -> ModelResponse:
    values = {
        "request_id": "req-1",
        "model": "fast",
        "provider": "openrouter",
        "provider_model": "vendor/model-a",
        "message": {"role": "assistant", "content": "안녕하세요"},
        "finish_reason": "stop",
        "usage": {"input_tokens": 10, "output_tokens": 3},
        "latency_ms": 120,
    }
    return ModelResponse.model_validate({**values, **changes})


def test_minimal_response():
    r = response()

    assert r.version == 1
    assert r.text() == "안녕하세요"
    assert r.usage.cost is None


def test_message_must_be_assistant():
    with pytest.raises(ValidationError, match="assistant"):
        response(message={"role": "user", "content": "x"})


def test_tool_calls_finish_needs_tool_calls():
    call = {"id": "c1", "name": "search", "arguments": {"q": "x"}}

    r = response(
        message={"role": "assistant", "tool_calls": [call]}, finish_reason="tool_calls"
    )
    assert r.text() == ""
    with pytest.raises(ValidationError, match="도구 호출이 없다"):
        response(finish_reason="tool_calls")


@pytest.mark.parametrize(
    "changes",
    [
        {"finish_reason": "max_tokens"},
        {"usage": {"input_tokens": -1, "output_tokens": 0}},
        {"usage": {"input_tokens": 1, "output_tokens": 1, "cost": "-0.01"}},
        {"latency_ms": -5},
        {"provider_model": ""},
        {"version": 2},
        {"raw": {"anything": 1}},
    ],
)
def test_bad_response_shape(changes):
    with pytest.raises(ValidationError):
        response(**changes)


def test_cost_keeps_precision():
    r = response(usage={"input_tokens": 1, "output_tokens": 1, "cost": "0.000123"})

    assert r.usage.cost == Decimal("0.000123")


def test_response_message_continues_conversation():
    # 응답의 message 를 그대로 다음 요청에 이어 붙일 수 있다.
    r = response()

    follow_up = ModelRequest(
        model="fast",
        messages=[
            Message(role="user", content="인사해"),
            r.message,
            Message(role="user", content="한 번 더"),
        ],
        params={"max_output_tokens": 50},
    )

    assert follow_up.messages[1].role == "assistant"


def test_round_trip_through_json():
    r = response(usage={"input_tokens": 1, "output_tokens": 2, "cost": "0.5"})

    assert ModelResponse.model_validate_json(r.model_dump_json()) == r


# --- 원하는 모양으로 읽기 ---


class Answer(BaseModel):
    title: str
    score: int


def test_parse_output_reads_requested_shape():
    r = response(message={"role": "assistant", "content": '{"title": "a", "score": 3}'})

    assert parse_output(r, Answer) == Answer(title="a", score=3)


@pytest.mark.parametrize(
    "text", ['{"title": "a"}', '{"title": "a", "score": "many"}', "그냥 말", ""]
)
def test_parse_output_rejects_wrong_shape(text):
    r = response(message={"role": "assistant", "content": text or "x"})
    if not text:
        r = response(
            message={
                "role": "assistant",
                "tool_calls": [{"id": "c", "name": "t", "arguments": {}}],
            },
            finish_reason="tool_calls",
        )

    with pytest.raises(ValidationError):
        parse_output(r, Answer)


# --- 실패 ---


@pytest.mark.parametrize(
    ("kind", "retryable"),
    [
        ("timeout", True),
        ("rate_limited", True),
        ("unavailable", True),
        ("invalid_request", False),
        ("auth", False),
        ("unknown", False),
    ],
)
def test_failure_retryable(kind, retryable):
    failure = ModelCallFailed(kind, "req-1", "무언가 잘못됨")

    assert failure.retryable is retryable
    assert failure.request_id == "req-1"
    assert kind in str(failure)
