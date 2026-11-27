import uuid
from datetime import timedelta

import pytest
from pydantic import BaseModel, ValidationError

from agent_builder_infra.services import redis_key

TTL = timedelta(minutes=1)


class Progress(BaseModel):
    step: int
    note: str


@pytest.fixture
def prefix(redis_service):
    """테스트마다 새 접두사를 쓰고, 끝나면 그 아래 키를 모두 지운다."""
    prefix = redis_key("test", uuid.uuid4())
    yield prefix
    keys = redis_service.scan_keys(f"{prefix}:*", limit=1000)
    if keys:
        redis_service.delete(*keys)


def test_redis_key():
    assert redis_key("run", 42, "progress") == "run:42:progress"


def test_str_sets_ttl(redis_service, prefix):
    key = redis_key(prefix, "s")
    redis_service.set_str(key, "값", ttl=TTL)

    assert redis_service.get_str(key) == "값"
    assert 0 < redis_service.get_ttl(key) <= 60
    assert redis_service.get_str(redis_key(prefix, "none")) is None


def test_json(redis_service, prefix):
    key = redis_key(prefix, "j")
    redis_service.set_json(key, {"a": [1, 2], "b": "한글"}, ttl=TTL)

    assert redis_service.get_json(key) == {"a": [1, 2], "b": "한글"}
    assert "한글" in redis_service.get_str(key)


def test_model(redis_service, prefix):
    key = redis_key(prefix, "m")
    redis_service.set_model(key, Progress(step=2, note="ok"), ttl=TTL)

    assert redis_service.get_model(key, Progress) == Progress(step=2, note="ok")
    assert redis_service.get_model(redis_key(prefix, "none"), Progress) is None


def test_model_rejects_wrong_shape(redis_service, prefix):
    key = redis_key(prefix, "m")
    redis_service.set_json(key, {"step": "not a number"}, ttl=TTL)

    with pytest.raises(ValidationError):
        redis_service.get_model(key, Progress)


def test_hash(redis_service, prefix):
    key = redis_key(prefix, "h")
    redis_service.hset(key, {"a": "1", "b": 2}, ttl=TTL)

    assert redis_service.hget(key, "a") == "1"
    assert redis_service.hgetall(key) == {"a": "1", "b": "2"}
    assert redis_service.get_ttl(key) > 0
    assert redis_service.hdel(key, "a") == 1
    assert redis_service.hgetall(key) == {"b": "2"}


def test_incr_sets_ttl_only_once(redis_service, prefix):
    key = redis_key(prefix, "c")

    assert redis_service.incr(key, ttl=TTL) == 1
    redis_service.expire(key, timedelta(seconds=30))
    assert redis_service.incr(key, 5, ttl=TTL) == 6
    # 두 번째 incr 이 수명을 1분으로 되돌리지 않았다.
    assert redis_service.get_ttl(key) <= 30


def test_key_functions(redis_service, prefix):
    key = redis_key(prefix, "k")
    redis_service.set_str(key, "v", ttl=TTL)

    assert redis_service.exists(key) is True
    assert redis_service.scan_keys(f"{prefix}:*") == [key]
    assert redis_service.delete(key) == 1
    assert redis_service.exists(key) is False
    assert redis_service.expire(key, TTL) is False
    assert redis_service.get_ttl(key) == -2
