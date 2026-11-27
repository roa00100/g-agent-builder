"""조립하는 곳. infra 의 프로바이더와 서비스를 프로세스에서 한 번씩 만든다.

Spring 의 DI 컨테이너 자리다. 실행할 때 조립하는 일이라 runtime 에 있다.
진입점(CLI·REST)은 프로바이더를 직접 만들지 않고 여기서 받는다.
테스트는 여기를 거치지 않고 프로바이더를 직접 만들어 서비스에 넣어도 된다.

from agent_builder_runtime.container import get_db
get_db().fetch_all("select ...")
"""

from functools import lru_cache

from agent_builder_infra.providers.object_storage import ObjectStorageProvider
from agent_builder_infra.providers.postgres import PostgresProvider
from agent_builder_infra.providers.redis import RedisProvider
from agent_builder_infra.services.db import DbService
from agent_builder_infra.services.object_storage import ObjectStorageService
from agent_builder_infra.services.redis import RedisService
from agent_builder_infra.settings import get_settings
from agent_builder_runtime.repositories import ModelCatalogRepository


@lru_cache
def get_postgres_provider() -> PostgresProvider:
    return PostgresProvider(get_settings().database_url)


@lru_cache
def get_redis_provider() -> RedisProvider:
    return RedisProvider(get_settings().redis_url)


@lru_cache
def get_object_storage_provider() -> ObjectStorageProvider:
    settings = get_settings()
    return ObjectStorageProvider(
        endpoint_url=settings.storage_endpoint_url,
        access_key=settings.storage_access_key,
        secret_key=settings.storage_secret_key.get_secret_value(),
        bucket=settings.storage_bucket,
    )


@lru_cache
def get_db() -> DbService:
    return DbService(get_postgres_provider())


@lru_cache
def get_redis() -> RedisService:
    return RedisService(get_redis_provider())


@lru_cache
def get_object_storage() -> ObjectStorageService:
    return ObjectStorageService(get_object_storage_provider())


@lru_cache
def get_model_catalog() -> ModelCatalogRepository:
    """core 의 ModelCatalog 를 채우는 구현."""
    return ModelCatalogRepository(get_db(), get_redis())


def close_all() -> None:
    """프로세스를 끝낼 때 부른다. 만든 적 없는 프로바이더는 만들지 않는다.

    부른 뒤에 get_* 를 다시 부르면 새로 만든다.
    """
    providers = (get_postgres_provider, get_redis_provider, get_object_storage_provider)
    for get_provider in providers:
        if get_provider.cache_info().currsize:
            get_provider().close()
    services = (get_db, get_redis, get_object_storage, get_model_catalog)
    for getter in (*providers, *services):
        getter.cache_clear()
