"""실제 PostgreSQL·Redis 에 붙는다.

model_alias 테이블이 있어야 한다(alembic upgrade head).
"""

import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from agent_builder_infra.model_alias import (
    DisabledModelAlias,
    ModelAlias,
    ModelAliasService,
    UnknownModelAlias,
)
from agent_builder_infra.model_alias.__main__ import main
from agent_builder_infra.services import redis_key


@pytest.fixture
def service(db, redis_service):
    return ModelAliasService(db, redis_service)


@pytest.fixture
def name(db, redis_service):
    """테스트마다 새 이름을 쓰고, 끝나면 줄과 캐시를 지운다."""
    name = f"test-{uuid.uuid4()}"
    yield name
    db.execute("delete from model_alias where name = :n", {"n": name})
    redis_service.delete(redis_key("model_alias", name))


def make(name: str, **changes) -> ModelAlias:
    values = {
        "name": name,
        "provider": "openrouter",
        "provider_model": "vendor/model-a",
        "input_kinds": ("text",),
    }
    return ModelAlias(**{**values, **changes})


def test_upsert_then_resolve(service, name):
    service.upsert(make(name, input_kinds=("text", "image")))

    alias = service.resolve(name)

    assert alias.provider_model == "vendor/model-a"
    assert alias.input_kinds == ("text", "image")


def test_unknown_name_is_error(service, name):
    assert service.get(name) is None
    with pytest.raises(UnknownModelAlias):
        service.resolve(name)


def test_get_fills_cache(service, name, redis_service):
    service.upsert(make(name))
    key = redis_key("model_alias", name)
    assert redis_service.exists(key) is False

    service.get(name)

    assert redis_service.get_model(key, ModelAlias) == make(name)
    assert 0 < redis_service.get_ttl(key) <= 300


def test_cache_is_used(service, name, redis_service, db):
    service.upsert(make(name))
    service.get(name)
    # DB 를 직접 바꿔도 캐시가 살아 있는 동안은 캐시 값이 나온다 — 캐시를 탄다는 확인.
    db.execute(
        "update model_alias set provider_model = 'changed' where name = :n", {"n": name}
    )

    assert service.get(name).provider_model == "vendor/model-a"


def test_upsert_clears_cache(service, name):
    service.upsert(make(name))
    service.get(name)

    service.upsert(make(name, provider_model="vendor/model-b"))

    assert service.resolve(name).provider_model == "vendor/model-b"


def test_disable_clears_cache_and_blocks(service, name):
    service.upsert(make(name))
    service.resolve(name)

    service.set_enabled(name, False)

    with pytest.raises(DisabledModelAlias):
        service.resolve(name)
    service.set_enabled(name, True)
    assert service.resolve(name).enabled is True


def test_set_enabled_unknown_is_error(service, name):
    with pytest.raises(UnknownModelAlias):
        service.set_enabled(name, False)


def test_delete(service, name):
    service.upsert(make(name))
    service.get(name)

    assert service.delete(name) is True
    assert service.get(name) is None
    assert service.delete(name) is False


def test_list_includes_row(service, name):
    service.upsert(make(name))

    assert make(name) in service.list()


def test_schema_rejects_unknown_kind(name):
    with pytest.raises(ValidationError):
        make(name, input_kinds=("video",))
    with pytest.raises(ValidationError):
        make(name, input_kinds=())


def test_table_rejects_unknown_kind(db, name):
    # 스키마를 거치지 않고 넣어도 테이블의 검사 제약이 막는다.
    with pytest.raises(IntegrityError):
        db.execute(
            "insert into model_alias (name, provider, provider_model, input_kinds)"
            " values (:n, 'p', 'm', array['video'])",
            {"n": name},
        )


def test_cli_set_show_disable_delete(name, capsys):
    assert (
        main(
            [
                "set",
                name,
                "--provider",
                "openrouter",
                "--model",
                "m",
                "--inputs",
                "text,file",
            ]
        )
        == 0
    )
    assert main(["show", name]) == 0
    assert '"provider_model": "m"' in capsys.readouterr().out

    assert main(["disable", name]) == 0
    assert "꺼짐" in capsys.readouterr().out

    assert main(["delete", name]) == 0
    assert main(["show", name]) == 1
    assert "대응표에 없는" in capsys.readouterr().err


def test_cli_rejects_bad_inputs(name, capsys):
    code = main(["set", name, "--provider", "p", "--model", "m", "--inputs", "video"])

    assert code == 2
