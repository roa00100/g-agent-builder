"""테이블 model_call 의 정의 — 성공·실패 줄의 제약.

실제 PostgreSQL 에 붙는다(alembic upgrade head).
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

INSERT = (
    "insert into model_call (request_id, model, provider, provider_model, status,"
    " finish_reason, input_tokens, output_tokens, cost, failure_kind, latency_ms,"
    " started_at) values (:id, 'fast', 'p', 'm', :status, :finish, :tin, :tout,"
    " :cost, :kind, 5, now())"
)
OK = {"status": "ok", "finish": "stop", "tin": 1, "tout": 2, "cost": 0.1, "kind": None}
FAILED = {
    "status": "failed",
    "finish": None,
    "tin": None,
    "tout": None,
    "cost": None,
    "kind": "timeout",
}


@pytest.fixture
def request_id(db):
    request_id = f"test-{uuid.uuid4()}"
    yield request_id
    db.execute("delete from model_call where request_id = :id", {"id": request_id})


@pytest.mark.parametrize("values", [OK, FAILED])
def test_accepts_ok_and_failed(db, request_id, values):
    db.execute(INSERT, {"id": request_id, **values})
    assert (
        db.fetch_value(
            "select status from model_call where request_id = :id", {"id": request_id}
        )
        == values["status"]
    )


@pytest.mark.parametrize(
    "values",
    [
        {**OK, "status": "maybe"},
        {**OK, "finish": "done"},
        {**OK, "finish": None},
        {**OK, "tin": None},
        {**OK, "kind": "timeout"},
        {**FAILED, "kind": None},
        {**FAILED, "kind": "boom"},
        {**FAILED, "finish": "stop"},
        {**OK, "cost": -1},
        {**OK, "tout": -1},
    ],
)
def test_rejects_inconsistent_rows(db, request_id, values):
    with pytest.raises(IntegrityError):
        db.execute(INSERT, {"id": request_id, **values})
