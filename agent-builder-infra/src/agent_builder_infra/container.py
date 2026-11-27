"""조립하는 곳. 프로바이더와 공통 서비스를 프로세스에서 한 번씩 만든다.

Spring 의 DI 컨테이너 자리다. 다른 모듈은 프로바이더를 직접 만들지 않고 여기서 받는다.
테스트는 여기를 거치지 않고 프로바이더를 직접 만들어 서비스에 넣어도 된다.

from agent_builder_infra.container import get_db
get_db().fetch_all("select ...")
"""

from functools import lru_cache

from agent_builder_infra.providers.postgres import PostgresProvider
from agent_builder_infra.providers.redis import RedisProvider
from agent_builder_infra.services.db import DbService
from agent_builder_infra.services.redis import RedisService
from agent_builder_infra.settings import get_settings


@lru_cache
def get_postgres_provider() -> PostgresProvider:
    return PostgresProvider(get_settings().database_url)


@lru_cache
def get_redis_provider() -> RedisProvider:
    return RedisProvider(get_settings().redis_url)


@lru_cache
def get_db() -> DbService:
    return DbService(get_postgres_provider())


@lru_cache
def get_redis() -> RedisService:
    return RedisService(get_redis_provider())


def close_all() -> None:
    """프로세스를 끝낼 때 부른다. 만든 적 없는 프로바이더는 만들지 않는다.

    부른 뒤에 get_* 를 다시 부르면 새로 만든다.
    """
    for get_provider in (get_postgres_provider, get_redis_provider):
        if get_provider.cache_info().currsize:
            get_provider().close()
    for getter in (get_postgres_provider, get_redis_provider, get_db, get_redis):
        getter.cache_clear()
