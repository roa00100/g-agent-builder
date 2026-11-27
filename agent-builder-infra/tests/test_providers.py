import pytest
from sqlalchemy.exc import OperationalError

from agent_builder_infra.providers import (
    ObjectStorageProvider,
    PostgresProvider,
    RedisProvider,
)


def test_postgres_ping(postgres_provider):
    assert postgres_provider.ping() is True
    assert postgres_provider.engine.dialect.name == "postgresql"


def test_redis_ping(redis_provider):
    assert redis_provider.ping() is True


def test_postgres_ping_raises_when_unreachable():
    # 1 번 포트에는 아무것도 없다. 붙지 못하면 False 가 아니라 예외가 나야 한다.
    # connect_timeout=1: 없으면 Windows 에서 포기하기까지 2분 넘게 걸린다.
    provider = PostgresProvider(
        "postgresql+psycopg://u:p@127.0.0.1:1/d?connect_timeout=1"
    )
    with pytest.raises(OperationalError):
        provider.ping()
    provider.close()


def test_redis_ping_raises_when_unreachable():
    from redis.exceptions import ConnectionError

    provider = RedisProvider("redis://127.0.0.1:1/0")
    with pytest.raises(ConnectionError):
        provider.ping()
    provider.close()


def test_object_storage_ping(object_storage_provider):
    assert object_storage_provider.ping() is True


def test_object_storage_rejects_wrong_secret(object_storage_provider):
    # 키가 틀리면 False 가 아니라 예외가 나야 한다.
    # 인증이 실제로 걸려 있다는 확인이기도 하다.
    from botocore.exceptions import ClientError

    from agent_builder_infra.settings import get_settings

    settings = get_settings()
    provider = ObjectStorageProvider(
        endpoint_url=settings.storage_endpoint_url,
        access_key=settings.storage_access_key,
        secret_key="wrong-secret",
        bucket=settings.storage_bucket,
    )
    with pytest.raises(ClientError):
        provider.ping()
    provider.close()


def test_object_storage_ping_raises_for_missing_bucket(object_storage_provider):
    from botocore.exceptions import ClientError

    from agent_builder_infra.settings import get_settings

    settings = get_settings()
    provider = ObjectStorageProvider(
        endpoint_url=settings.storage_endpoint_url,
        access_key=settings.storage_access_key,
        secret_key=settings.storage_secret_key.get_secret_value(),
        bucket="no-such-bucket",
    )
    with pytest.raises(ClientError):
        provider.ping()
    provider.close()
