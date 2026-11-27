"""모델 호출 서비스. 메모리 대응표와 가짜 공급자로 순서와 규칙을 확인한다."""

import pytest

from agent_builder_core.contracts.model import (
    CallLog,
    CallRecord,
    DisabledModel,
    ModelCallFailed,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ModelSpec,
    UnknownModel,
    UnknownProvider,
    UnsupportedInput,
)
from agent_builder_core.model import ModelGateway, ProviderMismatch, UnresolvedSource


class Catalog:
    def __init__(self, *specs: ModelSpec) -> None:
        self._specs = {spec.name: spec for spec in specs}

    def get(self, name: str) -> ModelSpec | None:
        return self._specs.get(name)


class FakeProvider:
    """받은 것을 기록하고, 정해 둔 응답이나 실패를 돌려준다."""

    name = "fake"

    def __init__(self, fail: ModelCallFailed | None = None, **response_changes) -> None:
        self.calls: list[tuple[ModelRequest, ModelSpec]] = []
        self._fail = fail
        self._changes = response_changes

    def complete(self, request: ModelRequest, spec: ModelSpec) -> ModelResponse:
        self.calls.append((request, spec))
        if self._fail is not None:
            raise self._fail
        values = {
            "request_id": request.request_id,
            "model": request.model,
            "provider": spec.provider,
            "provider_model": spec.provider_model,
            "message": {"role": "assistant", "content": "답"},
            "finish_reason": "stop",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "latency_ms": 1,
        }
        return ModelResponse.model_validate({**values, **self._changes})


def spec(**changes) -> ModelSpec:
    values = {
        "name": "fast",
        "provider": "fake",
        "provider_model": "vendor/model-a",
        "input_kinds": ("text",),
    }
    return ModelSpec(**{**values, **changes})


def request(content="안녕") -> ModelRequest:
    return ModelRequest(
        model="fast",
        messages=[{"role": "user", "content": content}],
        params={"max_output_tokens": 10},
    )


class MemoryLog:
    """남긴 기록을 모은다. broken 이면 남길 때 실패한다."""

    def __init__(self, broken: bool = False) -> None:
        self.records: list[CallRecord] = []
        self.errors: list[tuple[CallRecord, Exception]] = []
        self._broken = broken

    def record(self, record: CallRecord) -> None:
        if self._broken:
            raise ConnectionError("DB 끊김")
        self.records.append(record)

    def get(self, request_id: str) -> CallRecord | None:
        return next((r for r in self.records if r.request_id == request_id), None)

    def list(self, limit: int) -> list[CallRecord]:
        return self.records[::-1][:limit]

    def on_error(self, record: CallRecord, error: Exception) -> None:
        self.errors.append((record, error))


def gateway(
    provider: FakeProvider, *specs: ModelSpec, log: MemoryLog | None = None
) -> ModelGateway:
    log = log if log is not None else MemoryLog()
    return ModelGateway(
        Catalog(*(specs or (spec(),))),
        {provider.name: provider},
        log,
        log.on_error,
    )


def test_fake_provider_fills_contract():
    assert isinstance(FakeProvider(), ModelProvider)


def test_sends_to_provider_named_by_spec():
    provider = FakeProvider()

    response = gateway(provider).complete(request())

    assert response.text() == "답"
    sent_request, sent_spec = provider.calls[0]
    assert sent_spec.provider_model == "vendor/model-a"
    assert sent_request.model == "fast"


@pytest.mark.parametrize(
    ("specs", "error"),
    [
        ((), UnknownModel),
        ((spec(enabled=False),), DisabledModel),
        ((spec(provider="other"),), UnknownProvider),
    ],
)
def test_blocks_before_sending(specs, error):
    provider = FakeProvider()
    log = MemoryLog()
    gw = ModelGateway(Catalog(*specs), {provider.name: provider}, log, log.on_error)

    with pytest.raises(error):
        gw.complete(request())
    assert provider.calls == []
    # 보내기 전에 막힌 것은 기록하지 않는다.
    assert log.records == []


def test_blocks_unsupported_input():
    provider = FakeProvider()
    content = [
        {
            "type": "image",
            "source": {"type": "url", "url": "https://x.dev/a.png"},
            "media_type": "image/png",
        }
    ]

    with pytest.raises(UnsupportedInput):
        gateway(provider).complete(request(content))
    assert provider.calls == []


def test_blocks_stored_source_until_file_store_exists():
    provider = FakeProvider()
    content = [
        {
            "type": "file",
            "source": {"type": "stored", "file_id": "f-1"},
            "media_type": "application/pdf",
        }
    ]

    with pytest.raises(UnresolvedSource, match="f-1"):
        gateway(provider, spec(input_kinds=("text", "file"))).complete(request(content))
    assert provider.calls == []


def test_failure_passes_through_without_retry():
    failure = ModelCallFailed("rate_limited", "x", "잠시 뒤에")
    provider = FakeProvider(fail=failure)

    with pytest.raises(ModelCallFailed) as raised:
        gateway(provider).complete(request())
    assert raised.value is failure
    assert len(provider.calls) == 1


@pytest.mark.parametrize("changes", [{"request_id": "other"}, {"model": "smart"}])
def test_rejects_response_for_another_request(changes):
    provider = FakeProvider(**changes)

    log = MemoryLog()
    sent = request()

    with pytest.raises(ProviderMismatch):
        gateway(provider, log=log).complete(sent)
    # 보낸 것은 사실이라 실패로 남긴다. 응답의 숫자는 믿을 수 없어 넣지 않는다.
    (record,) = log.records
    assert (record.request_id, record.status, record.failure_kind) == (
        sent.request_id,
        "failed",
        "unknown",
    )
    assert record.input_tokens is None


# --- 기록 ---


def test_memory_log_fills_contract():
    assert isinstance(MemoryLog(), CallLog)


def test_success_is_recorded_with_numbers():
    log = MemoryLog()
    provider = FakeProvider(
        usage={"input_tokens": 7, "output_tokens": 3, "cost": "0.0002"},
        upstream_provider="OpenAI",
        latency_ms=42,
    )
    sent = request()

    gateway(provider, log=log).complete(sent)

    (record,) = log.records
    assert record.request_id == sent.request_id
    assert (record.model, record.provider, record.provider_model) == (
        "fast",
        "fake",
        "vendor/model-a",
    )
    assert record.upstream_provider == "OpenAI"
    assert (record.status, record.finish_reason) == ("ok", "stop")
    assert (record.input_tokens, record.output_tokens) == (7, 3)
    assert str(record.cost) == "0.0002"
    assert record.latency_ms == 42
    assert record.started_at.tzinfo is not None
    assert record.retryable is None


def test_failure_is_recorded_with_kind():
    log = MemoryLog()
    provider = FakeProvider(fail=ModelCallFailed("timeout", "x", "느림"))

    with pytest.raises(ModelCallFailed):
        gateway(provider, log=log).complete(request())

    (record,) = log.records
    assert (record.status, record.failure_kind, record.failure_detail) == (
        "failed",
        "timeout",
        "느림",
    )
    assert record.retryable is True
    assert record.input_tokens is None


def test_run_context_is_copied_to_record():
    log = MemoryLog()
    sent = ModelRequest(
        model="fast",
        messages=[{"role": "user", "content": "x"}],
        params={"max_output_tokens": 10},
        trace={"run_id": "run-1", "step_id": "step-2", "attempt": 3},
    )

    gateway(FakeProvider(), log=log).complete(sent)

    record = log.records[0]
    assert (record.run_id, record.step_id, record.attempt) == ("run-1", "step-2", 3)


def test_record_failure_keeps_the_response_and_is_reported():
    log = MemoryLog(broken=True)

    response = gateway(FakeProvider(), log=log).complete(request())

    assert response.text() == "답"
    ((record, error),) = log.errors
    assert record.status == "ok"
    assert isinstance(error, ConnectionError)


def test_record_failure_does_not_hide_the_call_failure():
    log = MemoryLog(broken=True)
    provider = FakeProvider(fail=ModelCallFailed("auth", "x", "키 틀림"))

    with pytest.raises(ModelCallFailed):
        gateway(provider, log=log).complete(request())
    assert log.errors[0][0].failure_kind == "auth"
