"""Redis 공통 동작.

Redis 에는 짧게 사는 것만 둔다(AGENTS.md 5절 결정). 그래서 값을 쓰는 메서드는 ttl 을
반드시 받는다. 남아야 하는 것은 Postgres 에 둔다.

key = redis_key("run", run_id, "progress")
redis.set_model(key, progress, ttl=timedelta(hours=1))
"""

import json
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from pydantic import BaseModel

from agent_builder_infra.providers.redis import RedisProvider


def redis_key(*parts: object) -> str:
    """("run", 42, "progress") → "run:42:progress". 콜론으로 잇는 것이 Redis 관례다."""
    return ":".join(str(part) for part in parts)


class RedisService:
    def __init__(self, provider: RedisProvider) -> None:
        self._client = provider.client

    # --- 문자열 ---

    def get_str(self, key: str) -> str | None:
        return self._client.get(key)

    def set_str(self, key: str, value: str, *, ttl: timedelta) -> None:
        self._client.set(key, value, ex=ttl)

    # --- JSON ---

    def get_json(self, key: str) -> Any:
        """없으면 None. 저장한 값이 JSON null 이어도 None 이라 둘을 구분하지 못한다."""
        raw = self.get_str(key)
        return None if raw is None else json.loads(raw)

    def set_json(self, key: str, value: Any, *, ttl: timedelta) -> None:
        # ensure_ascii=False: 한글을 \uXXXX 로 바꾸지 않아 redis-cli 로 볼 때 읽힌다.
        self.set_str(key, json.dumps(value, ensure_ascii=False), ttl=ttl)

    # --- Pydantic 모델 ---

    def get_model[M: BaseModel](self, key: str, model: type[M]) -> M | None:
        """없으면 None. 저장된 모양이 모델과 다르면 ValidationError.

        예전 모양으로 저장된 값을 조용히 넘기지 않으려는 것이다.
        """
        raw = self.get_str(key)
        return None if raw is None else model.model_validate_json(raw)

    def set_model(self, key: str, value: BaseModel, *, ttl: timedelta) -> None:
        self.set_str(key, value.model_dump_json(), ttl=ttl)

    # --- 해시 (필드 여러 개를 가진 키) ---

    def hget(self, key: str, field: str) -> str | None:
        return self._client.hget(key, field)

    def hgetall(self, key: str) -> dict[str, str]:
        return self._client.hgetall(key)

    def hset(
        self, key: str, mapping: Mapping[str, str | int | float], *, ttl: timedelta
    ) -> None:
        """필드를 쓰고 키 전체의 수명을 ttl 로 다시 잡는다.

        둘은 한 번에(MULTI) 적용된다.
        """
        pipe = self._client.pipeline()
        pipe.hset(key, mapping=dict(mapping))
        pipe.expire(key, ttl)
        pipe.execute()

    def hdel(self, key: str, *fields: str) -> int:
        """지운 필드 수."""
        return self._client.hdel(key, *fields)

    # --- 카운터 ---

    def incr(self, key: str, amount: int = 1, *, ttl: timedelta) -> int:
        """더한 뒤의 값.

        수명은 키가 처음 생길 때만 잡는다 — 더할 때마다 늘리지 않는다.
        """
        pipe = self._client.pipeline()
        pipe.incrby(key, amount)
        pipe.expire(key, ttl, nx=True)
        value, _ = pipe.execute()
        return value

    # --- 키 ---

    def exists(self, key: str) -> bool:
        return self._client.exists(key) == 1

    def delete(self, *keys: str) -> int:
        """지운 키 수."""
        return self._client.delete(*keys)

    def expire(self, key: str, ttl: timedelta) -> bool:
        """키가 없으면 False."""
        return self._client.expire(key, ttl)

    def get_ttl(self, key: str) -> int:
        """남은 수명(초). 키가 없으면 -2, 수명이 없으면 -1 (Redis 의 값 그대로)."""
        return self._client.ttl(key)

    def scan_keys(self, pattern: str = "*", *, limit: int = 100) -> list[str]:
        """패턴에 맞는 키를 limit 개까지.

        KEYS 는 모든 키를 한 번에 훑어 그동안 Redis 가 멈춘다. SCAN 으로 나눠 읽는다.
        limit 기본값 100 은 들여다보기용으로 충분하고,
        실수로 큰 목록을 모으지 않게 한다.
        """
        keys: list[str] = []
        for key in self._client.scan_iter(match=pattern):
            keys.append(key)
            if len(keys) >= limit:
                break
        return keys
