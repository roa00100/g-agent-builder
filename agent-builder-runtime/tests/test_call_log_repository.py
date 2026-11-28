"""호출 기록 Repository. 실제 PostgreSQL 에 붙는다.

model_call 테이블이 있어야 한다(alembic upgrade head).
기록 규칙 자체(성공·실패에 있어야 할 값)는 core 의 테스트가 저장소 없이 확인한다.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from agent_builder_core.contracts.model import CallLog, CallRecord
from agent_builder_runtime.repositories import CallLogRepository

# 다른 기록보다 늘 최근이 되게 먼 미래로 둔다 — list 가 이 테스트의 줄을 먼저 돌려주게.
FUTURE = datetime(2100, 1, 1, tzinfo=UTC)


@pytest.fixture
def log(db, object_storage):
    return CallLogRepository(db, object_storage)


@pytest.fixture
def ids(db, object_storage):
    """테스트마다 새 request_id 를 쓰고, 끝나면 그 줄과 본문을 지운다."""
    made: list[str] = []

    def new() -> str:
        made.append(f"test-{uuid.uuid4()}")
        return made[-1]

    yield new
    for request_id in made:
        db.execute("delete from model_call where request_id = :id", {"id": request_id})
        for key in object_storage.list_keys(f"model_call/{request_id}/"):
            object_storage.delete(key)


def ok(request_id: str, **changes) -> CallRecord:
    values = {
        "request_id": request_id,
        "model": "fast",
        "provider": "openrouter",
        "provider_model": "openai/gpt-4o-mini",
        "upstream_provider": "OpenAI",
        "status": "ok",
        "finish_reason": "stop",
        "input_tokens": 14,
        "output_tokens": 3,
        "cost": Decimal("0.00000285"),
        "latency_ms": 1015,
        "started_at": FUTURE,
        "run_id": "run-1",
        "step_id": "step-1",
        "attempt": 1,
    }
    return CallRecord(**{**values, **changes})


def failed(request_id: str, **changes) -> CallRecord:
    values = {
        "request_id": request_id,
        "model": "fast",
        "provider": "openrouter",
        "provider_model": "openai/gpt-4o-mini",
        "status": "failed",
        "failure_kind": "timeout",
        "failure_detail": "60초 안에 답이 없었다",
        "latency_ms": 60000,
        "started_at": FUTURE,
    }
    return CallRecord(**{**values, **changes})


def test_fulfils_contract(log):
    assert isinstance(log, CallLog)


@pytest.mark.parametrize("make", [ok, failed])
def test_record_then_get_is_the_same(log, ids, make):
    record = make(ids())

    log.record(record)

    assert log.get(record.request_id) == record


def test_cost_keeps_all_digits(log, ids):
    record = ok(ids(), cost=Decimal("0.000000123456789"))

    log.record(record)

    assert log.get(record.request_id).cost == Decimal("0.000000123456789")


def test_unknown_request_id(log, ids):
    assert log.get(ids()) is None


def test_list_is_newest_first_and_limited(log, ids):
    older, newer = ids(), ids()
    log.record(ok(older, started_at=FUTURE))
    log.record(failed(newer, started_at=FUTURE + timedelta(seconds=1)))

    got = log.list(2)

    assert [record.request_id for record in got] == [newer, older]
    assert log.list(1)[0].request_id == newer


def test_same_request_id_twice_fails(log, ids):
    request_id = ids()
    log.record(ok(request_id))

    with pytest.raises(IntegrityError):
        log.record(ok(request_id))


def test_body_round_trip_keeps_korean_and_odd_values(log, ids):
    request_id = ids()
    content = {"text": "안녕", "nested": {"n": 1.5}, "odd": Decimal("0.1")}

    key = log.save_body(request_id, "received", content)

    assert key == f"model_call/{request_id}/received.json"
    # JSON 으로 바로 못 적는 값(Decimal)은 글자로 남는다.
    assert log.read_body(key) == {"text": "안녕", "nested": {"n": 1.5}, "odd": "0.1"}


def test_unknown_body_is_none(log, ids):
    assert log.read_body(f"model_call/{ids()}/request.json") is None


def test_record_keeps_body_keys(log, ids):
    request_id = ids()
    keys = {
        "request": log.save_body(request_id, "request", {"a": 1}),
        "response": log.save_body(request_id, "response", {"b": 2}),
    }

    log.record(ok(request_id, bodies=keys))

    assert log.get(request_id).bodies == keys
    assert log.list(1)[0].bodies == keys
