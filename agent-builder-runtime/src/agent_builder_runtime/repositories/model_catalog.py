"""core 의 ModelCatalog 를 채운다.

infra 의 값(테이블 model_alias, Redis 캐시)을 ModelSpec 으로 바꾼다.
DB 기술(SQLAlchemy)은 직접 쓰지 않는다. infra 가 주는 것만 쓴다 —
트랜잭션(DbService), 공통 CRUD(crud), 캐시(RedisService).

Postgres 가 기준이고 Redis 는 읽기 캐시다.
찾기: Redis → 없으면 Postgres → 찾았으면 Redis 에 담는다.
      없는 이름은 캐싱하지 않는다.
고치기: Postgres 에 커밋한 뒤 그 이름의 캐시를 지운다.
        다음 찾기가 Postgres 에서 새로 읽는다.
"""

from datetime import timedelta

from agent_builder_core.contracts.model import ModelSpec, UnknownModel
from agent_builder_infra import crud
from agent_builder_infra.observability import get_logger
from agent_builder_infra.services import DbService, RedisService, redis_key
from agent_builder_infra.tables.model_alias import ModelAliasRow

# 캐시 수명 5분. 표는 거의 바뀌지 않고, 고칠 때 캐시를 바로 지우므로 수명은 안전망이다
# (고친 직후의 찾기가 옛 값을 다시 담는 드문 경우에도 5분 뒤에는 맞춰진다).
CACHE_TTL = timedelta(minutes=5)

log = get_logger(__name__)


class ModelCatalogRepository:
    """core 의 ModelCatalog 를 채운다."""

    def __init__(self, db: DbService, redis: RedisService) -> None:
        self._db = db
        self._redis = redis

    # --- 찾기 ---

    def get(self, name: str) -> ModelSpec | None:
        cached = self._redis.get_model(_cache_key(name), ModelSpec)
        if cached is not None:
            log.debug("model_catalog.cache", name=name, hit=True)
            return cached
        with self._db.session_scope() as session:
            row = crud.find_by_id(session, ModelAliasRow, name)
            spec = None if row is None else _to_spec(row)
        log.debug("model_catalog.cache", name=name, hit=False, found=spec is not None)
        if spec is not None:
            self._redis.set_model(_cache_key(name), spec, ttl=CACHE_TTL)
        return spec

    def list(self) -> list[ModelSpec]:
        """이름 순(기본 키 순). 들여다보기용이라 캐시를 거치지 않는다."""
        with self._db.session_scope() as session:
            return [_to_spec(row) for row in crud.find_all(session, ModelAliasRow)]

    # --- 고치기 ---

    def upsert(self, spec: ModelSpec) -> None:
        """한 트랜잭션 안에서 찾고, 없으면 만들고, 있으면 고친다.

        DB 의 on conflict 대신 이렇게 한다.
        SQLAlchemy 를 runtime 에서 쓰지 않기 위해서다.
        같은 이름을 동시에 처음 넣으면 한쪽이 기본 키 충돌로 실패할 수 있지만,
        사용자 한 명이라 그런 동시 쓰기는 없다고 본다.
        """
        values = _to_values(spec)
        with self._db.session_scope() as session:
            row = crud.find_by_id(session, ModelAliasRow, spec.name)
            if row is None:
                crud.create(session, ModelAliasRow, name=spec.name, **values)
            else:
                crud.update(session, row, **values)
        self._invalidate(spec.name)

    def set_enabled(self, name: str, enabled: bool) -> None:
        with self._db.session_scope() as session:
            row = crud.find_by_id(session, ModelAliasRow, name)
            if row is None:
                raise UnknownModel(f"대응표에 없는 모델 이름: {name}")
            crud.update(session, row, enabled=enabled)
        self._invalidate(name)

    def delete(self, name: str) -> bool:
        with self._db.session_scope() as session:
            row = crud.find_by_id(session, ModelAliasRow, name)
            if row is not None:
                crud.delete(session, row)
        self._invalidate(name)
        return row is not None

    def _invalidate(self, name: str) -> None:
        # 커밋이 끝난 뒤에 지운다 — 커밋 전에 지우면 그 사이 찾기가 옛 값을 다시 담는다.
        self._redis.delete(_cache_key(name))


def _cache_key(name: str) -> str:
    return redis_key("model_alias", name)


def _to_values(spec: ModelSpec) -> dict:
    """ModelSpec → 테이블 열 값 (이름 제외)."""
    return {
        "provider": spec.provider,
        "provider_model": spec.provider_model,
        "input_kinds": list(spec.input_kinds),
        "enabled": spec.enabled,
        "timeout_seconds": spec.timeout_seconds,
    }


def _to_spec(row: ModelAliasRow) -> ModelSpec:
    """테이블 한 줄 → ModelSpec.

    ModelSpec 의 필드 이름으로 행의 속성을 읽는다(from_attributes).
    계약에 없는 열(updated_at)은 읽지 않고, 계약에 필드가 늘었는데 행에 그 열이
    없으면 여기서 오류가 나 빠뜨린 것이 드러난다. list → tuple 도 Pydantic 이 바꾼다.
    """
    return ModelSpec.model_validate(row, from_attributes=True)
