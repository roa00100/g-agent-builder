"""core 의 ModelProvider 를 OpenRouter 로 채운다 — 흐름만 둔다.

연결 받기 → 대기 시간 고르기 → 보내기 → 걸린 시간 재기.
요청·응답을 맞바꾸는 일은 request.py·response.py, 실패 해석은 errors.py 가 한다.
보내고 받는 것은 infra 의 연결점(OpenRouterClient.chat)이 한다.
여기는 openai SDK 를 직접 쓰지 않는다.
"""

import time
from typing import Protocol

from agent_builder_core.contracts.model import (
    ModelCallFailed,
    ModelRequest,
    ModelResponse,
    ModelSpec,
)
from agent_builder_infra.clients.openrouter import OpenRouterCallError
from agent_builder_infra.observability import get_logger
from agent_builder_runtime.model_adapters.connections import ProviderConnection
from agent_builder_runtime.model_adapters.openrouter.errors import kind_for_call_error
from agent_builder_runtime.model_adapters.openrouter.request import to_payload
from agent_builder_runtime.model_adapters.openrouter.response import to_response
from agent_builder_runtime.repositories.provider_profile import MissingApiKey

log = get_logger(__name__)


class ConnectionSource(Protocol):
    """ProviderConnections 가 채운다. 테스트는 가짜로 채운다."""

    def get(self, name: str) -> ProviderConnection: ...


class OpenRouterAdapter:
    name = "openrouter"

    def __init__(self, connections: ConnectionSource) -> None:
        self._connections = connections

    def complete(self, request: ModelRequest, spec: ModelSpec) -> ModelResponse:
        payload = to_payload(request, spec)
        # 공급자 프로필에서 연결과 기본 대기 시간을 받는다. 없거나 꺼진 프로필이면
        # UnknownProvider 가 그대로 올라간다(조립·설정의 문제).
        try:
            provider = self._connections.get(self.name)
        except MissingApiKey as error:
            raise ModelCallFailed("auth", request.request_id, str(error)) from error
        # 모델별 대기 시간이 있으면 그것을, 없으면 공급자 기본값을 쓴다.
        timeout_seconds = spec.timeout_seconds or provider.timeout_seconds
        log.debug(
            "openrouter.send",
            provider_model=spec.provider_model,
            timeout_seconds=timeout_seconds,
            timeout_from="model" if spec.timeout_seconds else "provider",
        )
        # 보내는 본문 그대로. 키는 본문에 없다(연결점이 헤더로 붙인다).
        log.trace("openrouter.payload", payload=payload)
        started = time.monotonic()
        try:
            body = provider.connection.chat(payload, timeout_seconds=timeout_seconds)
        except OpenRouterCallError as error:
            log.debug(
                "openrouter.error",
                reason=error.reason,
                status_code=error.status_code,
                detail=error.detail,
            )
            raise ModelCallFailed(
                kind_for_call_error(error), request.request_id, error.detail
            ) from error
        latency_ms = int((time.monotonic() - started) * 1000)
        log.trace("openrouter.body", body=body)
        return to_response(body, request, spec, latency_ms)
