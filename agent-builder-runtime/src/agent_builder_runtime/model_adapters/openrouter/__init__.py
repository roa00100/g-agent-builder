"""OpenRouter 공급자 — core 의 ModelProvider 를 OpenRouter 로 채운다.

adapter.py   흐름 (연결 받기 → 대기 시간 → 보내기 → 시간 재기)
request.py   ModelRequest → OpenRouter 요청 본문
response.py  OpenRouter 응답 본문 → ModelResponse
errors.py    OpenRouter 의 오류 → 계약의 실패 종류
"""

from agent_builder_runtime.model_adapters.openrouter.adapter import (
    OpenRouterAdapter,
)
from agent_builder_runtime.model_adapters.openrouter.errors import kind_for_status

__all__ = ["OpenRouterAdapter", "kind_for_status"]
