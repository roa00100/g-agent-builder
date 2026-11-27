"""공통 서비스 — 프로바이더를 생성자로 받아 그 위의 공통 동작을 제공한다.

개념 패키지의 service.py(업무 로직)와 다르다. 여기는 모든 개념이 같이 쓰는 기반이다.
"""

from agent_builder_infra.services.db import DbService
from agent_builder_infra.services.redis import RedisService, redis_key

__all__ = ["DbService", "RedisService", "redis_key"]
