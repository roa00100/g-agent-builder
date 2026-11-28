"""조립하는 곳. infra 의 프로바이더와 서비스를 프로세스에서 한 번씩 만든다.

Spring 의 DI 컨테이너 자리다. 실행할 때 조립하는 일이라 runtime 에 있다.
진입점(CLI·REST)은 프로바이더를 직접 만들지 않고 여기서 받는다.
테스트는 여기를 거치지 않고 프로바이더를 직접 만들어 서비스에 넣어도 된다.

from agent_builder_runtime.container import get_db
get_db().fetch_all("select ...")
"""

from functools import lru_cache

from agent_builder_core.contracts.model import CallLog, ModelCatalog
from agent_builder_core.model import ModelGateway
from agent_builder_infra.clients.openrouter import OpenRouterClient
from agent_builder_infra.observability import traced
from agent_builder_infra.providers.object_storage import ObjectStorageProvider
from agent_builder_infra.providers.postgres import PostgresProvider
from agent_builder_infra.providers.redis import RedisProvider
from agent_builder_infra.services.cipher import FernetCipher
from agent_builder_infra.services.db import DbService
from agent_builder_infra.services.object_storage import ObjectStorageService
from agent_builder_infra.services.redis import RedisService
from agent_builder_infra.settings import get_settings
from agent_builder_runtime.model_adapters import (
    OpenRouterAdapter,
    ProviderConnections,
)
from agent_builder_runtime.observability import trace_gateway
from agent_builder_runtime.repositories import (
    CallLogRepository,
    ModelCatalogRepository,
    ProviderProfileRepository,
)


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
def get_model_catalog() -> ModelCatalog:
    """core 의 ModelCatalog 를 채우는 구현. 메서드마다 span 을 연다."""
    return traced(
        ModelCatalogRepository(get_db(), get_redis()),
        "ModelCatalogRepository",
        ("get", "list", "upsert", "set_enabled", "delete"),
    )


@lru_cache
def get_call_log() -> CallLog:
    """core 의 CallLog 를 채우는 구현 — 호출 기록. 메서드마다 span 을 연다."""
    return traced(
        CallLogRepository(get_db(), get_object_storage()),
        "CallLogRepository",
        ("record", "save_body", "read_body", "get", "list"),
    )


class MissingMasterKey(RuntimeError):
    """마스터 키(SECRET_ENCRYPTION_KEY)가 설정되어 있지 않다."""


@lru_cache
def get_cipher() -> FernetCipher:
    """비밀 값 암호화. 마스터 키(SECRET_ENCRYPTION_KEY)가 있어야 한다."""
    key = get_settings().secret_encryption_key
    if key is None:
        raise MissingMasterKey("SECRET_ENCRYPTION_KEY 가 없다 — .env 에 적는다")
    return FernetCipher(key.get_secret_value())


@lru_cache
def get_provider_profiles() -> ProviderProfileRepository:
    # 마스터 키는 키를 풀거나 넣을 때만 필요해서, 만들 함수를 넘긴다.
    # span 에는 메서드 이름만 남는다 — 넘긴 값(키 등)은 남지 않는다.
    return traced(
        ProviderProfileRepository(get_db(), get_redis(), get_cipher),
        "ProviderProfileRepository",
        ("get", "list", "api_key", "save", "set_api_key", "set_enabled", "delete"),
    )


@lru_cache
def get_provider_connections() -> ProviderConnections:
    """공급자 연결. 프로필이 바뀌면 연결을 새로 만든다.

    지금 공급자는 OpenRouter 하나라, 연결점도 OpenRouterClient 하나로 만든다.
    """
    connections = ProviderConnections(
        get_provider_profiles(),
        connect=lambda base_url, api_key: OpenRouterClient(
            api_key=api_key, base_url=base_url
        ),
    )
    return traced(connections, "ProviderConnections", ("get",))


@lru_cache
def get_model_gateway() -> ModelGateway:
    """모델 호출 서비스. 호출 하나가 span 하나다(trace_gateway).

    공급자는 이름으로 고른다 — 대응표의 ModelSpec.provider 와 같은 값.
    """
    openrouter = traced(
        OpenRouterAdapter(get_provider_connections()),
        "OpenRouterAdapter",
        ("complete",),
    )
    gateway = ModelGateway(
        get_model_catalog(),
        {openrouter.name: openrouter},
        get_call_log(),
    )
    return trace_gateway(gateway)


def close_all() -> None:
    """프로세스를 끝낼 때 부른다. 만든 적 없는 프로바이더는 만들지 않는다.

    부른 뒤에 get_* 를 다시 부르면 새로 만든다.
    """
    providers = (
        get_postgres_provider,
        get_redis_provider,
        get_object_storage_provider,
    )
    # 공급자 연결은 프로필마다 열려 있으므로 연결 관리자가 닫는다.
    if get_provider_connections.cache_info().currsize:
        get_provider_connections().close_all()
    for get_provider in providers:
        if get_provider.cache_info().currsize:
            get_provider().close()
    services = (
        get_db,
        get_redis,
        get_object_storage,
        get_model_catalog,
        get_call_log,
        get_cipher,
        get_provider_profiles,
        get_provider_connections,
        get_model_gateway,
    )
    for getter in (*providers, *services):
        getter.cache_clear()
