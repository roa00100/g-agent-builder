import pytest

from agent_builder_core.contracts.model import ModelCatalog
from agent_builder_core.model import ModelGateway
from agent_builder_infra.services import DbService, ObjectStorageService, RedisService
from agent_builder_infra.settings import get_settings
from agent_builder_runtime import container


def test_returns_one_instance_each():
    try:
        assert isinstance(container.get_db(), DbService)
        assert isinstance(container.get_redis(), RedisService)
        assert isinstance(container.get_object_storage(), ObjectStorageService)
        assert container.get_object_storage() is container.get_object_storage()
        assert isinstance(container.get_model_catalog(), ModelCatalog)
        assert container.get_model_catalog() is container.get_model_catalog()
        assert container.get_db() is container.get_db()
        assert container.get_redis() is container.get_redis()
    finally:
        container.close_all()


def test_close_all_then_rebuilds():
    first = container.get_db()
    assert first.fetch_value("select 1") == 1

    container.close_all()

    second = container.get_db()
    assert second is not first
    assert second.fetch_value("select 1") == 1
    container.close_all()


def test_model_gateway_is_built_without_any_key():
    # 키는 보낼 때 공급자 프로필에서 읽는다. 조립에는 키가 필요 없다.
    try:
        gateway = container.get_model_gateway()

        assert isinstance(gateway, ModelGateway)
        assert gateway is container.get_model_gateway()
    finally:
        container.close_all()


def test_cipher_needs_master_key(monkeypatch):
    monkeypatch.setenv("SECRET_ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    container.close_all()
    try:
        with pytest.raises(RuntimeError, match="SECRET_ENCRYPTION_KEY"):
            container.get_cipher()
    finally:
        container.close_all()
        get_settings.cache_clear()
