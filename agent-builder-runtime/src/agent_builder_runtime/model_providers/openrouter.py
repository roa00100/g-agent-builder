"""core 의 ModelProvider 를 OpenRouter 로 채운다.

요청·응답을 OpenRouter 의 모양과 맞바꾸고, 실패를 계약의 말(FailureKind)로 해석한다.
OpenRouter 를 어떻게 읽을지는 이 파일 한 곳에 둔다.
보내고 받는 것은 infra 의 연결점(OpenRouterProvider.chat)이 한다.
여기는 openai SDK 를 직접 쓰지 않는다.
OpenRouter 의 요청·응답 모양은 공식 문서(api-reference/overview, multimodal/pdfs,
structured-outputs, errors)를 따른다.
"""

import json
import time
from decimal import Decimal
from typing import Any, Protocol

from agent_builder_core.contracts.model import (
    ContentPart,
    FailureKind,
    FilePart,
    FinishReason,
    ImagePart,
    InlineSource,
    Message,
    ModelCallFailed,
    ModelRequest,
    ModelResponse,
    ModelSpec,
    TextPart,
    ToolCall,
    UrlSource,
)
from agent_builder_infra.providers.openrouter import OpenRouterCallError
from agent_builder_runtime.model_providers.connections import ProviderConnection
from agent_builder_runtime.repositories.provider_profile import MissingApiKey


class ConnectionSource(Protocol):
    """ProviderConnections 가 채운다. 테스트는 가짜로 채운다."""

    def get(self, name: str) -> ProviderConnection: ...


# OpenRouter 의 finish_reason 은 다섯 낱말로 정규화돼 온다:
#   stop·length·tool_calls·content_filter·error
# error 는 실패로 따로 다루고, 나머지 넷은 계약과 같은 낱말이다.
_FINISH_REASONS: frozenset[str] = frozenset(
    {"stop", "length", "tool_calls", "content_filter"}
)


class OpenRouterModelProvider:
    name = "openrouter"

    def __init__(self, connections: ConnectionSource) -> None:
        self._connections = connections

    def complete(self, request: ModelRequest, spec: ModelSpec) -> ModelResponse:
        payload = _to_payload(request, spec)
        # 공급자 프로필에서 연결과 기본 대기 시간을 받는다. 없거나 꺼진 프로필이면
        # UnknownProvider 가 그대로 올라간다(조립·설정의 문제).
        try:
            provider = self._connections.get(self.name)
        except MissingApiKey as error:
            raise ModelCallFailed("auth", request.request_id, str(error)) from error
        # 모델별 대기 시간이 있으면 그것을, 없으면 공급자 기본값을 쓴다.
        timeout_seconds = spec.timeout_seconds or provider.timeout_seconds
        started = time.monotonic()
        try:
            body = provider.connection.chat(payload, timeout_seconds=timeout_seconds)
        except OpenRouterCallError as error:
            raise ModelCallFailed(
                _kind_for_call_error(error), request.request_id, error.detail
            ) from error
        latency_ms = int((time.monotonic() - started) * 1000)
        return _to_response(body, request, spec, latency_ms)


# --- 요청: ModelRequest → OpenRouter 본문 ---


def _to_payload(request: ModelRequest, spec: ModelSpec) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    if request.system is not None:
        messages.append({"role": "system", "content": request.system})
    messages.extend(_to_message(message, request) for message in request.messages)

    params = request.params
    payload: dict[str, Any] = {
        "model": spec.provider_model,
        "messages": messages,
        "max_tokens": params.max_output_tokens,
    }
    if params.temperature is not None:
        payload["temperature"] = params.temperature
    if params.top_p is not None:
        payload["top_p"] = params.top_p
    if params.seed is not None:
        payload["seed"] = params.seed
    if params.stop:
        payload["stop"] = list(params.stop)
    if request.tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in request.tools
        ]
        payload["tool_choice"] = _to_tool_choice(request.tool_choice)
    if request.output is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": request.output.name,
                "strict": True,
                "schema": request.output.json_schema,
            },
        }
    return payload


def _to_tool_choice(choice: str) -> Any:
    # auto·none·required 는 그대로. 도구 이름이면 그 함수를 고르는 모양으로.
    # required 는 OpenRouter 문서의 타입에는 없지만 OpenAI 호환 모양이라 그대로 넘긴다 —
    # 문서상 지원하지 않는 값은 공급자가 무시한다.
    if choice in ("auto", "none", "required"):
        return choice
    return {"type": "function", "function": {"name": choice}}


def _to_message(message: Message, request: ModelRequest) -> dict[str, Any]:
    if message.role == "user":
        return {
            "role": "user",
            "content": [_to_part(part, request) for part in message.content],
        }
    text = "".join(part.text for part in message.content if isinstance(part, TextPart))
    if message.role == "tool":
        return {"role": "tool", "tool_call_id": message.tool_call_id, "content": text}
    out: dict[str, Any] = {"role": "assistant", "content": text or None}
    if message.tool_calls:
        out["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.arguments, ensure_ascii=False),
                },
            }
            for call in message.tool_calls
        ]
    return out


def _to_part(part: ContentPart, request: ModelRequest) -> dict[str, Any]:
    if isinstance(part, TextPart):
        return {"type": "text", "text": part.text}
    if isinstance(part, ImagePart):
        if isinstance(part.source, InlineSource):
            url = f"data:{part.media_type};base64,{part.source.data}"
        elif isinstance(part.source, UrlSource):
            url = str(part.source.url)
        else:
            raise _stored_source_reached(request)
        return {"type": "image_url", "image_url": {"url": url}}
    if isinstance(part, FilePart):
        if isinstance(part.source, InlineSource):
            return {
                "type": "file",
                "file": {
                    "filename": part.filename or "file",
                    "file_data": f"data:{part.media_type};base64,{part.source.data}",
                },
            }
        if isinstance(part.source, UrlSource):
            # OpenRouter 문서는 Chat Completions 의 파일을 base64 data URL 로만 보인다.
            # 주소로 보내도 되는지 확인되지 않아 보내기 전에 거절한다.
            raise ModelCallFailed(
                "invalid_request",
                request.request_id,
                "OpenRouter 로는 파일을 주소(url)로 보낼 수 없다 — "
                "내용(inline)으로 보낸다",
            )
        raise _stored_source_reached(request)
    raise TypeError(f"모르는 조각: {part!r}")


def _stored_source_reached(request: ModelRequest) -> ValueError:
    # ModelGateway 가 보내기 전에 막는다. 여기까지 왔으면 Gateway 를 거치지 않은 것이다.
    return ValueError(
        f"저장된 파일 출처는 내용으로 바꾼 뒤 보낸다 (request_id={request.request_id})"
    )


# --- 응답: OpenRouter 본문 → ModelResponse ---


def _to_response(
    body: dict[str, Any], request: ModelRequest, spec: ModelSpec, latency_ms: int
) -> ModelResponse:
    # OpenRouter 는 HTTP 200 이어도 본문에 오류만 담아 올 수 있다(choices 없음),
    # 또는 만들다 실패하면 choice 에 error 와 finish_reason="error" 를 담는다.
    choices = body.get("choices") or []
    if body.get("error") and not choices:
        raise _failed_from_body(body["error"], request)
    if not choices:
        raise ModelCallFailed("unknown", request.request_id, "응답에 choices 가 없다")
    choice = choices[0]
    if choice.get("error") or choice.get("finish_reason") == "error":
        raise _failed_from_body(choice.get("error") or {}, request)

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


def _failed_from_body(error: dict[str, Any], request: ModelRequest) -> ModelCallFailed:
    code = error.get("code")
    return ModelCallFailed(
        kind_for_status(code if isinstance(code, int) else None),
        request.request_id,
        str(error.get("message") or "공급자가 오류를 돌려줬다"),
    )


# --- 실패: OpenRouter 의 오류 → 계약의 실패 종류 ---


def _kind_for_call_error(error: OpenRouterCallError) -> FailureKind:
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
