"""Redis 연결. 클라이언트 하나를 프로세스 안에서 같이 쓴다.

파일 이름을 redis.py 로 하지 않는다 — 설치한 redis 패키지를 가려 import 가 꼬인다.
"""

from functools import lru_cache

from redis import Redis

from agent_builder_core.settings import get_settings


@lru_cache
def get_redis() -> Redis:
    # decode_responses=True: 값을 bytes 가 아니라 str 로 돌려준다.
    # 저장할 값은 Pydantic 이 만든 JSON 문자열이라 str 이 맞다.
    return Redis.from_url(get_settings().redis_url, decode_responses=True)
