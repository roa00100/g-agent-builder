"""모델 대응표 Repository. 실제 PostgreSQL·Redis 에 붙는다.

model_alias 테이블이 있어야 한다(alembic upgrade head).
계약 자체의 규칙(resolve_model 등)은 core 의 테스트가 저장소 없이 확인한다.
"""

import uuid

import pytest

from agent_builder_core.contracts.model import (
    DisabledModel,
    ModelCatalog,
    ModelSpec,
    UnknownModel,
    resolve_model,
)
from agent_builder_infra.services import redis_key
from agent_builder_runtime.repositories import ModelCatalogRepository


@pytest.fixture
def catalog(db, redis_service):
    return ModelCatalogRepository(db, redis_service)


@pytest.fixture
def name(db, redis_service):
    """테스트마다 새 이름을 쓰고, 끝나면 줄과 캐시를 지운다."""
    name = f"test-{uuid.uuid4()}"
    yield name
    db.execute("delete from model_alias where name = :n", {"n": name})
    redis_service.delete(redis_key("model_alias", name))


def make(name: str, **changes) -> ModelSpec:
    values = {
        "name": name,
        "provider": "openrouter",
        "provider_model": "vendor/model-a",
        "input_kinds": ("text",),
    }
    return ModelSpec(**{**values, **changes})


def test_fulfils_contract(catalog):
    assert isinstance(catalog, ModelCatalog)


def test_upsert_then_resolve(catalog, name):
    catalog.upsert(make(name, input_kinds=("text", "image")))

    spec = resolve_model(catalog, name)

    assert spec.provider_model == "vendor/model-a"
    assert spec.input_kinds == ("text", "image")


def test_unknown_name(catalog, name):
    assert catalog.get(name) is None
    with pytest.raises(UnknownModel):
        resolve_model(catalog, name)


def test_get_fills_cache(catalog, name, redis_service):
    catalog.upsert(make(name))
    key = redis_key("model_alias", name)
    assert redis_service.exists(key) is False

    catalog.get(name)

    assert redis_service.get_model(key, ModelSpec) == make(name)
    assert 0 < redis_service.get_ttl(key) <= 300


def test_cache_is_used(catalog, name, db):
    catalog.upsert(make(name))
    catalog.get(name)
    # DB 를 직접 바꿔도 캐시가 살아 있는 동안은 캐시 값이 나온다 — 캐시를 탄다는 확인.
    db.execute(
        "update model_alias set provider_model = 'changed' where name = :n", {"n": name}
    )

    assert catalog.get(name).provider_model == "vendor/model-a"


def test_upsert_clears_cache(catalog, name):
    catalog.upsert(make(name))
    catalog.get(name)

    catalog.upsert(make(name, provider_model="vendor/model-b"))

    assert resolve_model(catalog, name).provider_model == "vendor/model-b"


def test_disable_clears_cache_and_blocks(catalog, name):
    catalog.upsert(make(name))
    resolve_model(catalog, name)

    catalog.set_enabled(name, False)

    with pytest.raises(DisabledModel):
        resolve_model(catalog, name)
    catalog.set_enabled(name, True)
    assert resolve_model(catalog, name).enabled is True


def test_set_enabled_unknown_is_error(catalog, name):
    with pytest.raises(UnknownModel):
        catalog.set_enabled(name, False)


def test_delete(catalog, name):
    catalog.upsert(make(name))
    catalog.get(name)

    assert catalog.delete(name) is True
    assert catalog.get(name) is None
    assert catalog.delete(name) is False


def test_list_includes_row(catalog, name):
    catalog.upsert(make(name))

    assert make(name) in catalog.list()
