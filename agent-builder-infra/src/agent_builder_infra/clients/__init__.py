"""외부 API 접속 — 모델 공급자 같은 바깥 서비스의 API 를 부르는 클라이언트.

이름은 ~Client 로 짓는다.
저장소 접속(Postgres·Redis·오브젝트 스토리지)은 providers/ 의 ~Provider 다.
여기는 라이브러리를 불러 보내고 받는 데까지이고, 무엇을 보낼지·받은 것을 어떻게 읽을지는
runtime 의 어댑터가 정한다.
"""

from agent_builder_infra.clients.openrouter import (
    OPENROUTER_BASE_URL,
    OpenRouterCallError,
    OpenRouterClient,
)

__all__ = ["OPENROUTER_BASE_URL", "OpenRouterCallError", "OpenRouterClient"]
