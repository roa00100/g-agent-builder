"""OpenRouter 연결점 — 보내고 받기와 SDK 오류 넘기기.

네트워크 없이 가짜 전송(httpx.MockTransport)으로 돈다.
실패를 계약의 말로 해석하는 일은 runtime 의 테스트가 본다.
"""

import httpx
import pytest

from agent_builder_infra.providers import OpenRouterCallError, OpenRouterProvider

PAYLOAD = {"model": "vendor/model-a", "messages": [{"role": "user", "content": "x"}]}

OK_BODY = {
    "id": "gen-1",
    "object": "chat.completion",
    "created": 0,
    "model": "vendor/model-a",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "답"},
            "finish_reason": "stop",
            "native_finish_reason": "end_turn",
        }
    ],
    "usage": {
        "prompt_tokens": 3,
        "completion_tokens": 1,
        "total_tokens": 4,
        "cost": 0.000012,
    },
}


def provider(handler) -> OpenRouterProvider:
    return OpenRouterProvider(
        api_key="test-key",
        base_url="http://openrouter.test/api/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_chat_returns_body_with_fields_sdk_does_not_know():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["path"] = request.url.path
        return httpx.Response(200, json=OK_BODY)

    body = provider(handler).chat(PAYLOAD, timeout_seconds=5)

    assert body["choices"][0]["message"]["content"] == "답"
    # SDK 타입에 없는 필드도 남는다 — 비용과 원래 종료 사유를 읽어야 한다.
    assert body["usage"]["cost"] == 0.000012
    assert body["choices"][0]["native_finish_reason"] == "end_turn"
    assert seen == {"auth": "Bearer test-key", "path": "/api/v1/chat/completions"}


def test_error_body_with_200_is_returned_as_is():
    # HTTP 200 인데 본문에 오류만 든 경우 — 연결점은 가르지 않고 넘긴다.
    error_body = {"error": {"code": 503, "message": "공급자 없음"}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=error_body)

    assert (
        provider(handler).chat(PAYLOAD, timeout_seconds=5)["error"]
        == error_body["error"]
    )


@pytest.mark.parametrize("status", [400, 401, 402, 429, 503])
def test_http_error_keeps_status_and_body_and_sends_once(status):
    calls = []
    error_body = {"error": {"code": status, "message": "x"}}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status, json=error_body)

    with pytest.raises(OpenRouterCallError) as raised:
        provider(handler).chat(PAYLOAD, timeout_seconds=5)

    assert raised.value.reason == "http"
    assert raised.value.status_code == status
    assert raised.value.body == error_body["error"] or raised.value.body == error_body
    # SDK 의 자동 재시도를 껐다 — 한 번만 보낸다.
    assert len(calls) == 1


def test_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("느림", request=request)

    with pytest.raises(OpenRouterCallError) as raised:
        provider(handler).chat(PAYLOAD, timeout_seconds=5)

    assert raised.value.reason == "timeout"
    assert raised.value.status_code is None


def test_connection_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("못 붙음", request=request)

    with pytest.raises(OpenRouterCallError) as raised:
        provider(handler).chat(PAYLOAD, timeout_seconds=5)

    assert raised.value.reason == "connection"
