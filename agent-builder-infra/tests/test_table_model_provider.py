"""테이블 model_provider 와 model_alias.timeout_seconds 의 정의.

실제 PostgreSQL 에 붙는다(alembic upgrade head).
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def name(db):
    name = f"test-{uuid.uuid4()}"
    yield name
    db.execute("delete from model_provider where name = :n", {"n": name})
    db.execute("delete from model_alias where name = :n", {"n": name})


def test_provider_defaults(db, name):
    db.execute(
        "insert into model_provider (name, base_url, timeout_seconds)"
        " values (:n, 'https://x.dev', 60)",
        {"n": name},
    )

    row = db.fetch_one(
        "select api_key_enc, enabled from model_provider where name = :n", {"n": name}
    )

    assert row == {"api_key_enc": None, "enabled": True}


@pytest.mark.parametrize("timeout", [0, -1])
def test_provider_timeout_must_be_positive(db, name, timeout):
    with pytest.raises(IntegrityError):
        db.execute(
            "insert into model_provider (name, base_url, timeout_seconds)"
            " values (:n, 'https://x.dev', :t)",
            {"n": name, "t": timeout},
        )


def test_model_timeout_is_optional_but_positive(db, name):
    insert = (
        "insert into model_alias (name, provider, provider_model, input_kinds,"
        " timeout_seconds) values (:n, 'p', 'm', array['text'], :t)"
    )
    db.execute(insert, {"n": name, "t": None})
    db.execute("delete from model_alias where name = :n", {"n": name})

    with pytest.raises(IntegrityError):
        db.execute(insert, {"n": name, "t": 0})
