"""OpenRouter 응답 본문 → ModelResponse.

HTTP 200 이어도 본문이 오류일 수 있어, 그 경우는 응답이 아니라 ModelCallFailed 로 낸다.
"""

import json
from decimal import Decimal
from typing import Any

from agent_builder_core.contracts.model import (
    FinishReason,
    Message,
    ModelCallFailed,
    ModelRequest,
    ModelResponse,
    ModelSpec,
    TextPart,
    ToolCall,
)
from agent_builder_runtime.model_adapters.openrouter.errors import failure_from_body

# OpenRouter 의 finish_reason 은 다섯 낱말로 정규화돼 온다:
#   stop·length·tool_calls·content_filter·error
# error 는 실패로 따로 다루고, 나머지 넷은 계약과 같은 낱말이다.
_FINISH_REASONS: frozenset[str] = frozenset(
    {"stop", "length", "tool_calls", "content_filter"}
)


def to_response(
    body: dict[str, Any], request: ModelRequest, spec: ModelSpec, latency_ms: int
) -> ModelResponse:
    # OpenRouter 는 HTTP 200 이어도 본문에 오류만 담아 올 수 있다(choices 없음),
    # 또는 만들다 실패하면 choice 에 error 와 finish_reason="error" 를 담는다.
    choices = body.get("choices") or []
    if body.get("error") and not choices:
        raise failure_from_body(body["error"], request)
    if not choices:
        raise ModelCallFailed("unknown", request.request_id, "응답에 choices 가 없다")
    choice = choices[0]
    if choice.get("error") or choice.get("finish_reason") == "error":
        raise failure_from_body(choice.get("error") or {}, request)

    raw = choice.get("message") or {}
    tool_calls = tuple(
        _to_tool_call(call, request) for call in raw.get("tool_calls") or []
    )
    content = raw.get("content")
    message = Message(
        role="assistant",
        content=(TextPart(text=content),) if content else (),
        tool_calls=tool_calls,
    )

    reported = choice.get("finish_reason")
    finish_reason: FinishReason = (
        reported if reported in _FINISH_REASONS else "other"  # type: ignore[assignment]
    )
    if finish_reason == "tool_calls" and not tool_calls:
        # 공급자가 도구를 부른다고 하고 호출을 안 붙인 경우.
        # 계약을 어기지 않게 other 로.
        finish_reason = "other"

    usage = body.get("usage") or {}
    cost = usage.get("cost")
    return ModelResponse(
        request_id=request.request_id,
        model=request.model,
        provider=spec.provider,
        # 실제로 답한 모델. OpenRouter 가 다른 모델로 넘겼으면 명세의 이름과 다르다.
        provider_model=body.get("model") or spec.provider_model,
        message=message,
        finish_reason=finish_reason,
        finish_detail=choice.get("native_finish_reason") or reported,
        usage={
            "input_tokens": usage.get("prompt_tokens") or 0,
            "output_tokens": usage.get("completion_tokens") or 0,
            # OpenRouter 의 단위는 크레딧이다.
            # float 를 str 로 거쳐 Decimal 로 — 이진 오차를 막는다.
            "cost": None if cost is None else Decimal(str(cost)),
        },
        latency_ms=latency_ms,
        # OpenRouter 가 실제로 넘긴 곳 (예: OpenAI). 본문 맨 위의 provider 에 온다.
        upstream_provider=body.get("provider") or None,
    )


def _to_tool_call(call: dict[str, Any], request: ModelRequest) -> ToolCall:
    function = call.get("function") or {}
    try:
        arguments = json.loads(function.get("arguments") or "{}")
    except json.JSONDecodeError as error:
        raise ModelCallFailed(
            "unknown",
            request.request_id,
            f"도구 {function.get('name')} 의 인자가 JSON 이 아니다",
        ) from error
    return ToolCall(id=call["id"], name=function["name"], arguments=arguments)
