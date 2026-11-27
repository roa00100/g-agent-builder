"""호출 기록 한 줄의 규칙 — 성공·실패에 따라 있어야 할 값."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from agent_builder_core.contracts.model import CallRecord

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)

BASE = {
    "request_id": "r-1",
    "model": "fast",
    "provider": "openrouter",
    "provider_model": "openai/gpt-4o-mini",
    "latency_ms": 10,
    "started_at": NOW,
}
OK = {
    **BASE,
    "status": "ok",
    "finish_reason": "stop",
    "input_tokens": 1,
    "output_tokens": 2,
}
FAILED = {**BASE, "status": "failed", "failure_kind": "rate_limited"}


def test_ok_and_failed_shapes():
    assert CallRecord(**OK).retryable is None
    assert CallRecord(**FAILED).retryable is True


@pytest.mark.parametrize(
    "values",
    [
        {**OK, "finish_reason": None},
        {**OK, "input_tokens": None},
        {**OK, "failure_kind": "timeout"},
        {**FAILED, "failure_kind": None},
        {**FAILED, "finish_reason": "stop"},
        {**OK, "started_at": datetime(2026, 11, 27, 12, 0)},  # 시간대 없음
        {**OK, "cost": "-1"},
        {**OK, "extra": 1},  # 봉투 규칙
    ],
)
def test_rejects_inconsistent_records(values):
    with pytest.raises(ValidationError):
        CallRecord(**values)


def test_is_frozen():
    record = CallRecord(**OK)
    with pytest.raises(ValidationError):
        record.cost = 1
