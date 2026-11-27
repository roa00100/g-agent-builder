"""실제 PostgreSQL·Redis 에 붙는 픽스처.

먼저 `docker compose up -d --wait` 로 띄운다.
container 를 거치지 않고 프로바이더를 직접 만들어 서비스에 넣는다.
"""

import pytest

from agent_builder_infra.providers import PostgresProvider, RedisProvider
from agent_builder_infra.services import DbService, RedisService
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
