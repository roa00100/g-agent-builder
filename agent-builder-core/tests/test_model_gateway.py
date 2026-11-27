"""모델 호출 서비스. 메모리 대응표와 가짜 공급자로 순서와 규칙을 확인한다."""

import pytest

from agent_builder_core.contracts.model import (
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


def gateway(provider: FakeProvider, *specs: ModelSpec) -> ModelGateway:
    return ModelGateway(Catalog(*(specs or (spec(),))), {provider.name: provider})


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
    gw = ModelGateway(Catalog(*specs), {provider.name: provider})

    with pytest.raises(error):
        gw.complete(request())
    assert provider.calls == []


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

    with pytest.raises(ProviderMismatch):
        gateway(provider).complete(request())
