"""모델 호출 입구(명령줄 model call, REST POST /model/call).

가짜 Gateway 로 돈다 — 네트워크·비용 없이 입구가 번역만 하는지 확인한다.
실제 호출은 대응표에 모델을 등록한 뒤 손으로 확인한다.
"""

import pytest
from fastapi.testclient import TestClient

from agent_builder_core.contracts.model import (
    DisabledModel,
    ModelCallFailed,
    ModelRequest,
    ModelResponse,
    UnknownModel,
    UnknownProvider,
    UnsupportedInput,
)
from agent_builder_runtime.__main__ import main
from agent_builder_runtime.cli import model as cli_model
from agent_builder_runtime.container import get_model_gateway
from agent_builder_runtime.rest import create_app


class FakeGateway:
    def __init__(self, error: Exception | None = None) -> None:
        self.requests: list[ModelRequest] = []
        self._error = error

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return ModelResponse(
            request_id=request.request_id,
            model=request.model,
            provider="openrouter",
            provider_model="vendor/model-a",
            message={"role": "assistant", "content": "안녕하세요"},
            finish_reason="stop",
            finish_detail="end_turn",
            usage={"input_tokens": 5, "output_tokens": 2, "cost": "0.0001"},
            latency_ms=321,
        )


@pytest.fixture
def use_gateway(monkeypatch):
    """명령줄이 쓸 Gateway 를 가짜로 바꾼다."""

    def install(gateway: FakeGateway) -> FakeGateway:
        monkeypatch.setattr(cli_model, "get_model_gateway", lambda: gateway)
        return gateway

    return install


# --- 명령줄 ---


def test_cli_call_prints_only_text(use_gateway, capsys):
    gateway = use_gateway(FakeGateway())

    code = main(
        ["model", "call", "fast", "인사해", "--system", "짧게", "--max-tokens", "50"]
    )

    out, err = capsys.readouterr()
    assert code == 0
    assert out.strip() == "안녕하세요"
    # 요약은 로그(model.call.done)가 맡는다 — 명령이 따로 찍지 않는다.
    assert "vendor/model-a" not in err
    sent = gateway.requests[0]
    assert (sent.model, sent.system, sent.params.max_output_tokens) == (
        "fast",
        "짧게",
        50,
    )
    assert sent.messages[0].content[0].text == "인사해"


def test_cli_max_tokens_is_required(use_gateway):
    use_gateway(FakeGateway())

    with pytest.raises(SystemExit):
        main(["model", "call", "fast", "x"])


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (UnknownModel("없음"), 1),
        (DisabledModel("꺼짐"), 1),
        (UnknownProvider("공급자 없음"), 1),
        (UnsupportedInput("이미지 못 받음"), 2),
        (ModelCallFailed("rate_limited", "req-1", "잠시 뒤에"), 3),
    ],
)
def test_cli_errors_become_exit_codes(use_gateway, capsys, error, code):
    use_gateway(FakeGateway(error=error))

    assert main(["model", "call", "fast", "x", "--max-tokens", "10"]) == code
    if code == 3:
        err = capsys.readouterr().err
        assert "rate_limited" in err
        assert "다시 보내 볼 만함" in err


def test_cli_rejects_bad_max_tokens(use_gateway):
    use_gateway(FakeGateway())

    assert main(["model", "call", "fast", "x", "--max-tokens", "0"]) == 2


# --- REST ---


def rest(gateway: FakeGateway) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    return TestClient(app)


REQUEST = {
    "model": "fast",
    "messages": [{"role": "user", "content": "인사해"}],
    "params": {"max_output_tokens": 50},
}


def test_rest_call_returns_model_response():
    gateway = FakeGateway()

    with rest(gateway) as client:
        response = client.post("/model/call", json=REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["message"]["content"][0]["text"] == "안녕하세요"
    assert body["usage"]["cost"] == "0.0001"
    assert body["request_id"] == gateway.requests[0].request_id


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (UnknownModel("없음"), 404),
        (DisabledModel("꺼짐"), 409),
        (UnsupportedInput("이미지 못 받음"), 422),
        (UnknownProvider("공급자 없음"), 503),
    ],
)
def test_rest_errors_become_status(error, status):
    with rest(FakeGateway(error=error)) as client:
        assert client.post("/model/call", json=REQUEST).status_code == status


def test_rest_call_failure_is_502_with_kind():
    error = ModelCallFailed("timeout", "req-9", "느림")

    with rest(FakeGateway(error=error)) as client:
        response = client.post("/model/call", json=REQUEST)

    assert response.status_code == 502
    assert response.json() == {
        "kind": "timeout",
        "retryable": True,
        "detail": "느림",
        "request_id": "req-9",
    }


def test_rest_rejects_bad_request_shape():
    with rest(FakeGateway()) as client:
        bad = {**REQUEST, "params": {}}
        assert client.post("/model/call", json=bad).status_code == 422
