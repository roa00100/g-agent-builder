"""모델 호출 입구(명령줄 model call, REST POST /model/call).

가짜 Gateway 로 돈다 — 네트워크·비용 없이 입구가 번역만 하는지 확인한다.
실제 호출은 대응표에 모델을 등록한 뒤 손으로 확인한다.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from agent_builder_core.contracts.model import (
    CallNotRecorded,
    CallRecord,
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
from agent_builder_runtime.container import get_call_log, get_model_gateway
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
        (UnknownModel("nosuch"), 1),
        (DisabledModel("fast"), 1),
        (UnknownProvider("openrouter", "no_profile"), 1),
        (UnsupportedInput("fast", ("image",), ("text",)), 2),
        (ModelCallFailed("rate_limited", "req-1", "잠시 뒤에"), 3),
    ],
)
def test_cli_errors_become_exit_codes(use_gateway, capsys, error, code):
    use_gateway(FakeGateway(error=error))

    assert main(["model", "call", "fast", "x", "--max-tokens", "10"]) == code
    if code == 3:
        err = capsys.readouterr().err
        assert "호출 한도를 넘었다" in err
        assert "다시 보내 볼 만합니다" in err
        assert "model call-show req-1 --body" in err


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
        (UnknownModel("nosuch"), 404),
        (DisabledModel("fast"), 409),
        (UnsupportedInput("fast", ("image",), ("text",)), 422),
        (UnknownProvider("openrouter", "no_profile"), 503),
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
    body = response.json()
    assert {
        k: body[k] for k in ("kind", "retryable", "sent", "detail", "request_id")
    } == {
        "kind": "timeout",
        "retryable": True,
        "sent": True,
        "detail": "느림",
        "request_id": "req-9",
    }
    # 사람이 읽는 문장도 같이 온다 (명령줄과 같은 문장).
    assert body["message"].startswith("답을 받지 못했습니다")
    assert "원인 — 느림" in body["facts"]


def test_rest_rejects_bad_request_shape():
    with rest(FakeGateway()) as client:
        bad = {**REQUEST, "params": {}}
        assert client.post("/model/call", json=bad).status_code == 422


# --- 호출 기록 보기 ---

RECORD = CallRecord(
    request_id="r-1",
    model="fast",
    provider="openrouter",
    provider_model="vendor/model-a",
    status="ok",
    finish_reason="stop",
    input_tokens=5,
    output_tokens=2,
    cost="0.0001",
    latency_ms=321,
    started_at=datetime(2026, 11, 27, 12, 0, tzinfo=UTC),
)
FAILED_RECORD = RECORD.model_copy(
    update={
        "request_id": "r-2",
        "status": "failed",
        "finish_reason": None,
        "input_tokens": None,
        "output_tokens": None,
        "cost": None,
        "failure_kind": "timeout",
    }
)


class FakeLog:
    def __init__(self, *records: CallRecord) -> None:
        self.records = list(records)
        self.limits: list[int] = []

    def record(self, record: CallRecord) -> None:
        self.records.append(record)

    def save_body(self, request_id: str, name: str, content: dict) -> str:
        return f"{request_id}/{name}"

    def read_body(self, key: str) -> dict | None:
        return None

    def get(self, request_id: str) -> CallRecord | None:
        return next((r for r in self.records if r.request_id == request_id), None)

    def list(self, limit: int) -> list[CallRecord]:
        self.limits.append(limit)
        return self.records[:limit]


@pytest.fixture
def use_log(monkeypatch):
    def install(log: FakeLog) -> FakeLog:
        monkeypatch.setattr(cli_model, "get_call_log", lambda: log)
        return log

    return install


def test_cli_calls_prints_one_line_each(use_log, capsys):
    log = use_log(FakeLog(RECORD, FAILED_RECORD))

    assert main(["model", "calls", "--limit", "5"]) == 0

    lines = capsys.readouterr().out.strip().splitlines()
    assert log.limits == [5]
    assert len(lines) == 2
    assert "r-1" in lines[0] and "5/2" in lines[0] and "0.0001" in lines[0]
    assert "실패:timeout" in lines[1]


def test_cli_calls_rejects_bad_limit(use_log):
    use_log(FakeLog())
    assert main(["model", "calls", "--limit", "0"]) == 2


def test_cli_call_show(use_log, capsys):
    use_log(FakeLog(RECORD))

    assert main(["model", "call-show", "r-1"]) == 0
    assert '"request_id": "r-1"' in capsys.readouterr().out
    assert main(["model", "call-show", "nope"]) == 1


def test_rest_calls_and_one_call():
    app = create_app()
    log = FakeLog(RECORD, FAILED_RECORD)
    app.dependency_overrides[get_call_log] = lambda: log

    with TestClient(app) as client:
        listed = client.get("/model/calls", params={"limit": 1})
        one = client.get("/model/calls/r-2")
        missing = client.get("/model/calls/nope")
        bad = client.get("/model/calls", params={"limit": 0})

    assert listed.status_code == 200
    assert [item["request_id"] for item in listed.json()] == ["r-1"]
    assert listed.json()[0]["cost"] == "0.0001"
    assert one.json()["failure_kind"] == "timeout"
    assert missing.status_code == 404
    assert bad.status_code == 422


# --- 기록하지 못한 결과 · 본문 보기 ---


def test_cli_not_recorded_is_exit_4(use_gateway, capsys):
    error = CallNotRecorded("req-3", "response", sent=True, detail="스토리지 끊김")
    use_gateway(FakeGateway(error=error))

    assert main(["model", "call", "fast", "x", "--max-tokens", "10"]) == 4
    err = capsys.readouterr().err
    assert "답을 받았지만 기록을 남기지 못해 쓰지 않았습니다" in err
    assert "비용이 들었을 수 있습니다" in err
    assert "req-3" in err


def test_rest_not_recorded_is_503_with_stage():
    error = CallNotRecorded("req-4", "request", sent=False, detail="스토리지 끊김")

    with rest(FakeGateway(error=error)) as client:
        response = client.post("/model/call", json=REQUEST)

    assert response.status_code == 503
    body = response.json()
    assert {k: body[k] for k in ("kind", "stage", "sent", "detail", "request_id")} == {
        "kind": "not_recorded",
        "stage": "request",
        "sent": False,
        "detail": "스토리지 끊김",
        "request_id": "req-4",
    }
    assert body["message"] == "호출하지 않았습니다 — 기록 저장소에 쓸 수 없습니다."


WITH_BODIES = RECORD.model_copy(
    update={"request_id": "r-9", "bodies": {"request": "k/request"}}
)


class BodyLog(FakeLog):
    def save_body(self, request_id, name, content):
        return f"k/{name}"

    def read_body(self, key):
        return {"보낸": "말"} if key == "k/request" else None


def test_cli_call_show_with_body(use_log, capsys):
    use_log(BodyLog(WITH_BODIES))

    assert main(["model", "call-show", "r-9", "--body"]) == 0
    out = capsys.readouterr().out
    assert "--- request (k/request) ---" in out
    assert '"보낸": "말"' in out


def test_rest_call_body():
    app = create_app()
    app.dependency_overrides[get_call_log] = lambda: BodyLog(WITH_BODIES)

    with TestClient(app) as client:
        found = client.get("/model/calls/r-9/bodies/request")
        missing = client.get("/model/calls/r-9/bodies/response")
        bad_name = client.get("/model/calls/r-9/bodies/nope")

    assert found.json() == {"보낸": "말"}
    assert missing.status_code == 404
    assert bad_name.status_code == 422
