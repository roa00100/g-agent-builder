"""대응표를 읽고 고친다. Postgres 가 기준이고 Redis 는 읽기 캐시다.

읽기: Redis → 없으면 Postgres → 찾았으면 Redis 에 담는다.
      없는 이름은 캐싱하지 않는다.
고치기: Postgres 에 커밋한 뒤 그 이름의 캐시를 지운다.
        다음 읽기가 Postgres 에서 새로 읽는다.
"""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from agent_builder_infra.model_alias.models import ModelAliasRow
from agent_builder_infra.model_alias.schemas import ModelAlias
from agent_builder_infra.services.db import DbService
from agent_builder_infra.services.redis import RedisService, redis_key

# 캐시 수명 5분. 표는 거의 바뀌지 않고, 고칠 때 캐시를 바로 지우므로 수명은 안전망이다
# (고친 직후의 읽기가 옛 값을 다시 담는 드문 경우에도 5분 뒤에는 맞춰진다).
CACHE_TTL = timedelta(minutes=5)


class UnknownModelAlias(LookupError):
    """대응표에 없는 논리 이름. 기본 모델로 넘기지 않는다."""


class DisabledModelAlias(LookupError):
    """대응표에 있지만 꺼 둔 논리 이름."""


class ModelAliasService:
    def __init__(self, db: DbService, redis: RedisService) -> None:
        self._db = db
        self._redis = redis

    # --- 읽기 ---

    def get(self, name: str) -> ModelAlias | None:
        """한 줄. 없으면 None. 꺼 둔 줄도 돌려준다(enabled=False)."""
        cached = self._redis.get_model(_cache_key(name), ModelAlias)
        if cached is not None:
            return cached
        with self._db.session_scope() as session:
            row = session.get(ModelAliasRow, name)
            alias = None if row is None else _to_schema(row)
        if alias is not None:
            self._redis.set_model(_cache_key(name), alias, ttl=CACHE_TTL)
        return alias

    def resolve(self, name: str) -> ModelAlias:
        """모델 요청에 쓸 한 줄. 없거나 꺼져 있으면 오류다."""
        alias = self.get(name)
        if alias is None:
            raise UnknownModelAlias(f"대응표에 없는 모델 이름: {name}")
        if not alias.enabled:
            raise DisabledModelAlias(f"꺼 둔 모델 이름: {name}")
        return alias

    def list(self) -> list[ModelAlias]:
        """전부, 이름 순. 들여다보기용이라 캐시를 거치지 않는다."""
        with self._db.session_scope() as session:
            rows = session.scalars(select(ModelAliasRow).order_by(ModelAliasRow.name))
            return [_to_schema(row) for row in rows]

    # --- 고치기 ---

    def upsert(self, alias: ModelAlias) -> None:
        """이름이 없으면 넣고, 있으면 바꾼다."""
        values = {
            "name": alias.name,
            "provider": alias.provider,
            "provider_model": alias.provider_model,
            "input_kinds": list(alias.input_kinds),
            "enabled": alias.enabled,
        }
        statement = insert(ModelAliasRow).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[ModelAliasRow.name],
            set_={
                **{key: statement.excluded[key] for key in values if key != "name"},
                "updated_at": func.now(),
            },
        )
        with self._db.session_scope() as session:
            session.execute(statement)
        self._invalidate(alias.name)

    def set_enabled(self, name: str, enabled: bool) -> None:
        """켜거나 끈다. 없는 이름이면 오류다."""
        with self._db.session_scope() as session:
            row = session.get(ModelAliasRow, name)
            if row is None:
                raise UnknownModelAlias(f"대응표에 없는 모델 이름: {name}")
            row.enabled = enabled
        self._invalidate(name)

    def delete(self, name: str) -> bool:
        """지운다. 지웠으면 True, 없었으면 False."""
        with self._db.session_scope() as session:
            row = session.get(ModelAliasRow, name)
            if row is not None:
                session.delete(row)
        self._invalidate(name)
        return row is not None

    def _invalidate(self, name: str) -> None:
        # 커밋이 끝난 뒤에 지운다 — 커밋 전에 지우면 그 사이 읽기가 옛 값을 다시 담는다.
        self._redis.delete(_cache_key(name))


def _cache_key(name: str) -> str:
    return redis_key("model_alias", name)


def _to_schema(row: ModelAliasRow) -> ModelAlias:
    return ModelAlias(
        name=row.name,
        provider=row.provider,
        provider_model=row.provider_model,
        input_kinds=tuple(row.input_kinds),
        enabled=row.enabled,
    )
