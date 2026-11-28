"""ModelRequest → OpenRouter 요청 본문.

OpenRouter 문서(api-reference/overview, multimodal/pdfs, structured-outputs)를 따른다.
"""

import json
from typing import Any

from agent_builder_core.contracts.model import (
    ContentPart,
    FilePart,
    ImagePart,
    InlineSource,
    Message,
    ModelCallFailed,
    ModelRequest,
    ModelSpec,
    TextPart,
    UrlSource,
)


def to_payload(request: ModelRequest, spec: ModelSpec) -> dict[str, Any]:
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
                sent=False,
            )
        raise _stored_source_reached(request)
    raise TypeError(f"모르는 조각: {part!r}")


def _stored_source_reached(request: ModelRequest) -> ValueError:
    # ModelGateway 가 보내기 전에 막는다. 여기까지 왔으면 Gateway 를 거치지 않은 것이다.
    return ValueError(
        f"저장된 파일 출처는 내용으로 바꾼 뒤 보낸다 (request_id={request.request_id})"
    )
