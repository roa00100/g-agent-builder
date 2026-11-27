"""실제 Redis 에 붙는다. 먼저 `docker compose up -d --wait` 로 Redis 를 띄운다."""

import uuid

from agent_builder_core.redis_client import get_redis


def test_connects_to_redis():
    assert get_redis().ping() is True


def test_writes_and_reads_a_string():
    redis = get_redis()
    # 다른 키와 부딪히지 않게 테스트마다 새 키를 쓴다.
    key = f"test:{uuid.uuid4()}"
    try:
        redis.set(key, '{"step": 1}')
        assert redis.get(key) == '{"step": 1}'
    finally:
        redis.delete(key)
