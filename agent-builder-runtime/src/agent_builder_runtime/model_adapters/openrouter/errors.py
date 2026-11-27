"""OpenRouter 의 오류 → 계약의 실패 종류(FailureKind).

연결점의 오류(OpenRouterCallError)와 HTTP 200 본문 속 오류를 같은 표로 읽는다.
"""

from typing import Any

from agent_builder_core.contracts.model import (
    FailureKind,
    ModelCallFailed,
    ModelRequest,
)
from agent_builder_infra.clients.openrouter import OpenRouterCallError


def kind_for_call_error(error: OpenRouterCallError) -> FailureKind:
    if error.reason == "timeout":
        return "timeout"
    if error.reason == "connection":
        return "unavailable"
    return kind_for_status(error.status_code)


def kind_for_status(status_code: int | None) -> FailureKind:
    """HTTP 상태 코드(또는 OpenRouter 본문 오류의 code)를 실패 종류로.

    OpenRouter 문서(api-reference/errors) 기준:
      400·404·413·422 요청 문제, 403 거절(가드레일·검열) → invalid_request
      401 키                                             → auth
      408 시간 초과                                      → timeout
      429 한도                                           → rate_limited
      5xx 공급자 장애                                    → unavailable
      402 크레딧 부족은 맞는 종류가 없어 unknown — 다시 보내도 같다.
    """
    if status_code in (400, 403, 404, 413, 422):
        return "invalid_request"
    if status_code == 401:
        return "auth"
    if status_code == 408:
        return "timeout"
    if status_code == 429:
        return "rate_limited"
    if status_code is not None and status_code >= 500:
        return "unavailable"
    return "unknown"


def failure_from_body(error: dict[str, Any], request: ModelRequest) -> ModelCallFailed:
    code = error.get("code")
    return ModelCallFailed(
        kind_for_status(code if isinstance(code, int) else None),
        request.request_id,
        str(error.get("message") or "공급자가 오류를 돌려줬다"),
    )
