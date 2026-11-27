"""실제 PostgreSQL·Redis·오브젝트 스토리지에 붙는 픽스처.

먼저 `docker compose up -d --wait` 로 띄운다.

프로바이더를 직접 만들어 서비스에 넣는다(조립하는 container 는 runtime 에 있다).
"""

import pytest

from agent_builder_infra.providers import (
    ObjectStorageProvider,
    PostgresProvider,
    RedisProvider,
)
from agent_builder_infra.services import DbService, ObjectStorageService, RedisService
from agent_builder_infra.settings import get_settings


@pytest.fixture(scope="session")
def postgres_provider():
    provider = PostgresProvider(get_settings().database_url)
    yield provider
    provider.close()


@pytest.fixture(scope="session")
def redis_provider():
    provider = RedisProvider(get_settings().redis_url)
    yield provider
    provider.close()


@pytest.fixture
def db(postgres_provider):
    return DbService(postgres_provider)


@pytest.fixture
def redis_service(redis_provider):
    return RedisService(redis_provider)


@pytest.fixture(scope="session")
def object_storage_provider():
    settings = get_settings()
    provider = ObjectStorageProvider(
        endpoint_url=settings.storage_endpoint_url,
        access_key=settings.storage_access_key,
        secret_key=settings.storage_secret_key.get_secret_value(),
        bucket=settings.storage_bucket,
    )
    yield provider
    provider.close()


@pytest.fixture
def object_storage(object_storage_provider):
    return ObjectStorageService(object_storage_provider)
