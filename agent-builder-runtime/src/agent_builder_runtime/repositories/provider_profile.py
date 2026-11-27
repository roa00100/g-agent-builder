"""공급자 프로필 — 공급자에 어떻게 붙는가(주소·API 키·기본 대기 시간·켜짐).

core 의 계약이 아니다. 붙는 방법은 runtime 과 infra 만 안다. core 는 키를 모른다.

Postgres(테이블 model_provider)가 기준이고 Redis 는 읽기 캐시다.
모델 대응표와 같은 방식이다.
API 키는 평문으로 어디에도 두지 않는다. DB 에도, 캐시에도 암호문(Fernet)으로 있고,
보낼 때만 api_key() 로 푼다.
"""

from collections.abc import Callable
from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from agent_builder_core.contracts.model import UnknownProvider
from agent_builder_infra import crud
from agent_builder_infra.observability import get_logger
from agent_builder_infra.services import (
    DbService,
    FernetCipher,
    RedisService,
    redis_key,
)
from agent_builder_infra.tables.model_provider import ModelProviderRow

# 캐시 수명 5분. 모델 대응표와 같은 까닭 — 고칠 때 바로 지우므로 수명은 안전망이다.
CACHE_TTL = timedelta(minutes=5)

log = get_logger(__name__)


class MissingApiKey(RuntimeError):
    """공급자 프로필에 API 키를 아직 넣지 않았다."""


class ProviderProfile(BaseModel):
    """프로필 한 줄. 캐시(Redis)에 담는 것도 이것이다 — 키는 암호문 그대로."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        # 암호문(bytes)을 JSON 캐시에 담을 때 base64 로 적고 읽는다.
        ser_json_bytes="base64",
        val_json_bytes="base64",
    )

    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    api_key_enc: bytes | None
    timeout_seconds: float = Field(gt=0)
    enabled: bool
    # 프로필이 바뀌었는지 — 연결을 새로 만들지 가르는 데 쓴다.
    updated_at: datetime

    @property
    def has_api_key(self) -> bool:
        return self.api_key_enc is not None


class ProviderProfileRepository:
    def __init__(
        self,
        db: DbService,
        redis: RedisService,
        cipher: Callable[[], FernetCipher],
    ) -> None:
        self._db = db
        self._redis = redis
        # 마스터 키가 있어야 만들 수 있다. 키를 풀거나 넣을 때만 부른다 —
        # 목록 보기 같은 일은 마스터 키 없이도 된다.
        self._cipher = cipher

    # --- 찾기 ---

    def get(self, name: str) -> ProviderProfile | None:
        cached = self._redis.get_model(_cache_key(name), ProviderProfile)
        if cached is not None:
            log.debug("provider_profile.cache", name=name, hit=True)
            return cached
        with self._db.session_scope() as session:
            row = crud.find_by_id(session, ModelProviderRow, name)
            profile = None if row is None else _to_profile(row)
        log.debug(
            "provider_profile.cache", name=name, hit=False, found=profile is not None
        )
        if profile is not None:
            self._redis.set_model(_cache_key(name), profile, ttl=CACHE_TTL)
        return profile

    def list(self) -> list[ProviderProfile]:
        """이름 순. 들여다보기용이라 캐시를 거치지 않는다."""
        with self._db.session_scope() as session:
            return [
                _to_profile(row) for row in crud.find_all(session, ModelProviderRow)
            ]

    def api_key(self, profile: ProviderProfile) -> str:
        """키를 푼다. 보낼 때만 부른다. 키가 없으면 MissingApiKey."""
        if profile.api_key_enc is None:
            raise MissingApiKey(f"공급자 {profile.name} 에 API 키가 없다")
        return self._cipher().decrypt(profile.api_key_enc)

    # --- 고치기 ---

    def save(
        self, name: str, *, base_url: str, timeout_seconds: float, enabled: bool = True
    ) -> None:
        """비밀이 아닌 값을 넣거나 바꾼다.

        키는 건드리지 않는다 — 키는 set_api_key 로 넣는다.
        """
        values = {
            "base_url": base_url,
            "timeout_seconds": timeout_seconds,
            "enabled": enabled,
        }
        with self._db.session_scope() as session:
            row = crud.find_by_id(session, ModelProviderRow, name)
            if row is None:
                crud.create(session, ModelProviderRow, name=name, **values)
            else:
                crud.update(session, row, **values)
        self._invalidate(name)

    def set_api_key(self, name: str, api_key: str) -> None:
        """키를 암호화해 넣는다. 없는 공급자면 UnknownProvider."""
        if not api_key:
            raise ValueError("API 키가 비어 있다")
        token = self._cipher().encrypt(api_key)
        self._update(name, api_key_enc=token)

    def set_enabled(self, name: str, enabled: bool) -> None:
        self._update(name, enabled=enabled)

    def delete(self, name: str) -> bool:
        with self._db.session_scope() as session:
            row = crud.find_by_id(session, ModelProviderRow, name)
            if row is not None:
                crud.delete(session, row)
        self._invalidate(name)
        return row is not None

    def _update(self, name: str, **values: object) -> None:
        with self._db.session_scope() as session:
            row = crud.find_by_id(session, ModelProviderRow, name)
            if row is None:
                raise UnknownProvider(f"공급자 프로필이 없다: {name}")
            crud.update(session, row, **values)
        self._invalidate(name)

    def _invalidate(self, name: str) -> None:
        # 커밋이 끝난 뒤에 지운다 — 커밋 전에 지우면 그 사이 찾기가 옛 값을 다시 담는다.
        self._redis.delete(_cache_key(name))


def _cache_key(name: str) -> str:
    return redis_key("model_provider", name)


def _to_profile(row: ModelProviderRow) -> ProviderProfile:
    return ProviderProfile.model_validate(row, from_attributes=True)
