"""runtime 의 관측 — Gateway 호출이 span·로그로 남는지, container 가 감싸는지.

가짜 카탈로그·공급자로 돈다. 네트워크·비용은 없다.
"""

import json

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agent_builder_core.contracts.model import (
    ModelCallFailed,
    ModelCatalog,
    ModelRequest,
    ModelResponse,
    ModelSpec,
)
from agent_builder_core.model import ModelGateway
from agent_builder_infra.observability import configure_logging
from agent_builder_runtime import container
from agent_builder_runtime.observability import setup_observability, trace_gateway

SPANS = InMemorySpanExporter()


@pytest.fixture(scope="module", autouse=True)
def tracing():
    # 전역 추적 설정은 한 번뿐이라, 켠 설정에 메모리 수집기를 하나 더 단다.
    setup_observability()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(SPANS))


@pytest.fixture(autouse=True)
def clear_spans():
    SPANS.clear()


SPEC = ModelSpec(
    name="fast",
    provider="fake",
    provider_model="vendor/model-a",
    input_kinds=("text",),
)


class OneModel:
    def get(self, name):
        return SPEC if name == "fast" else None


class FakeProvider:
    name = "fake"

    def __init__(self, error=None):
        self._error = error

    def complete(self, request, spec):
        if self._error is not None:
            raise self._error
        return ModelResponse(
            request_id=request.request_id,
            model=request.model,
            provider="fake",
            provider_model=spec.provider_model,
            message={"role": "assistant", "content": "답"},
            finish_reason="stop",
            usage={"input_tokens": 3, "output_tokens": 1, "cost": "0.0002"},
            latency_ms=12,
        )


def request(text="보낼 말"):
    return ModelRequest(
        model="fast",
        messages=[{"role": "user", "content": text}],
        params={"max_output_tokens": 10},
    )


def lines(err: str) -> list[dict]:
    return [json.loads(line) for line in err.splitlines() if line.startswith("{")]


def test_call_is_one_span_with_numbers_and_one_info_line(capsys):
    configure_logging("INFO", "json")
    gateway = trace_gateway(ModelGateway(OneModel(), {"fake": FakeProvider()}))

    sent = request()
    gateway.complete(sent)

    assert isinstance(gateway, ModelGateway)
    finished = SPANS.get_finished_spans()
    assert [item.name for item in finished] == ["ModelGateway.complete"]
    attributes = dict(finished[0].attributes)
    assert attributes["model.alias"] == "fast"
    assert attributes["model.request_id"] == sent.request_id
    assert attributes["model.provider_model"] == "vendor/model-a"
    assert attributes["model.output_tokens"] == 1
    assert attributes["model.cost"] == "0.0002"
    # 오간 문장은 span 에 넣지 않는다.
    assert "보낼 말" not in json.dumps(attributes, ensure_ascii=False)

    logged = lines(capsys.readouterr().err)
    assert [line["event"] for line in logged] == ["model.call.done"]
    assert logged[0]["cost"] == "0.0002"
    assert logged[0]["trace_id"] == format(finished[0].context.trace_id, "032x")


def test_trace_level_logs_request_and_response(capsys):
    configure_logging("TRACE", "json")
    gateway = trace_gateway(ModelGateway(OneModel(), {"fake": FakeProvider()}))

    gateway.complete(request("비밀 아닌 문장"))

    events = [line["event"] for line in lines(capsys.readouterr().err)]
    assert events == ["model.request", "model.call.done", "model.response"]
    configure_logging("INFO", "json")


def test_failure_is_warning_and_span_error(capsys):
    configure_logging("INFO", "json")
    error = ModelCallFailed("rate_limited", "req", "잠시 뒤")
    gateway = trace_gateway(ModelGateway(OneModel(), {"fake": FakeProvider(error)}))

    with pytest.raises(ModelCallFailed):
        gateway.complete(request())

    finished = SPANS.get_finished_spans()[0]
    assert not finished.status.is_ok
    assert finished.attributes["model.failure"] == "rate_limited"
    logged = lines(capsys.readouterr().err)
    assert [(line["event"], line["level"]) for line in logged] == [
        ("model.call.failed", "warning")
    ]


def test_container_keeps_contract_types_after_wrapping():
    try:
        assert isinstance(container.get_model_catalog(), ModelCatalog)
        assert isinstance(container.get_model_gateway(), ModelGateway)
    finally:
        container.close_all()


def test_rest_request_is_root_span_with_gateway_inside():
    from fastapi.testclient import TestClient

    from agent_builder_runtime.container import get_model_gateway
    from agent_builder_runtime.rest import create_app

    app = create_app()
    gateway = trace_gateway(ModelGateway(OneModel(), {"fake": FakeProvider()}))
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    body = {
        "model": "fast",
        "messages": [{"role": "user", "content": "x"}],
        "params": {"max_output_tokens": 10},
    }
    with TestClient(app) as client:
        assert client.post("/model/call", json=body).status_code == 200
        client.get("/health")

    finished = {item.name: item for item in SPANS.get_finished_spans()}
    root = finished["POST /model/call"]
    assert root.parent is None
    assert finished["ModelGateway.complete"].context.trace_id == root.context.trace_id
    # /health 는 남기지 않는다.
    assert not any("health" in name for name in finished)


class NoModels:
    def get(self, name):
        return None


class WrongAnswer(FakeProvider):
    def complete(self, request, spec):
        return super().complete(request, spec).model_copy(update={"model": "other"})


@pytest.mark.parametrize(
    ("gateway", "event", "level"),
    [
        # 보내기 전에 막힘 — 부른 쪽의 문제.
        (ModelGateway(NoModels(), {}), "model.call.rejected", "warning"),
        # 보낸 뒤 응답이 요청과 맞지 않음 — 구현의 결함.
        (
            ModelGateway(OneModel(), {"fake": WrongAnswer()}),
            "model.call.error",
            "error",
        ),
    ],
)
def test_rejected_before_sending_is_told_apart_from_other_errors(
    capsys, gateway, event, level
):
    configure_logging("INFO", "json")

    with pytest.raises(Exception):  # noqa: B017 — 종류는 아래 로그로 본다
        trace_gateway(gateway).complete(request())

    logged = lines(capsys.readouterr().err)
    assert [(line["event"], line["level"]) for line in logged] == [(event, level)]
