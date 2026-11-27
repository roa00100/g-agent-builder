"""테이블 model_alias 의 정의. 실제 PostgreSQL 에 붙는다(alembic upgrade head)."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def name(db):
    name = f"test-{uuid.uuid4()}"
    yield name
    db.execute("delete from model_alias where name = :n", {"n": name})


def test_accepts_known_kinds(db, name):
    db.execute(
        "insert into model_alias (name, provider, provider_model, input_kinds)"
        " values (:n, 'p', 'm', array['text', 'image', 'file'])",
        {"n": name},
    )

    row = db.fetch_one("select enabled from model_alias where name = :n", {"n": name})

    assert row == {"enabled": True}


def test_table_rejects_unknown_kind(db, name):
    # Repository 를 거치지 않고 넣어도 테이블의 검사 제약이 막는다.
    with pytest.raises(IntegrityError):
        db.execute(
            "insert into model_alias (name, provider, provider_model, input_kinds)"
            " values (:n, 'p', 'm', array['video'])",
            {"n": name},
        )


def test_table_rejects_empty_kinds(db, name):
    with pytest.raises(IntegrityError):
        db.execute(
            "insert into model_alias (name, provider, provider_model, input_kinds)"
            " values (:n, 'p', 'm', array[]::text[])",
            {"n": name},
        )
