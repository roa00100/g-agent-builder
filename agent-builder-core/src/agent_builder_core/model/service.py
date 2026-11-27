"""모델 호출 서비스.

대응표 찾기, 맞는지 보기, 공급자 고르기, 보내기, 기록하기를 한 순서로 묶는다.

cli·rest·assist 는 이 서비스를 부르기만 한다. 공급자를 직접 고르지 않는다.
"""

import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

from agent_builder_core.contracts.model import (
    CallLog,
    CallRecord,
    FailureKind,
    ModelCallFailed,
    ModelCatalog,
    ModelRequest,
    ModelResponse,
    ModelSpec,
    StoredSource,
    check_inputs,
    resolve_model,
)
from agent_builder_core.contracts.model.content import FilePart, ImagePart
from agent_builder_core.contracts.model.provider import ModelProvider, UnknownProvider


class UnresolvedSource(ValueError):
    """요청에 저장된 파일(StoredSource)이 있는데 아직 내용으로 바꿀 수단이 없다.

    FileStore 계약이 생기면 Gateway 가 보내기 전에 내용으로 바꾼다.
    """


class ProviderMismatch(RuntimeError):
    """공급자가 돌려준 응답이 보낸 요청과 맞지 않는다 — 구현의 결함이다."""


# 기록에 실패했을 때 부른다 — (남기려던 기록, 난 예외).
# 알리는 방법은 조립하는 쪽이 정한다.
RecordErrorHandler = Callable[[CallRecord, Exception], None]


class ModelGateway:
    def __init__(
        self,
        catalog: ModelCatalog,
        providers: Mapping[str, ModelProvider],
        calls: CallLog,
        on_record_error: RecordErrorHandler,
    ) -> None:
        """on_record_error: 기록이 실패해도 호출은 실패로 보지 않는다(사용자가 고름).
        돈은 이미 썼고 답도 받았으니, 답까지 버리면 손해가 두 배다.
        대신 그 사실을 이 함수로 알린다 — 조용히 버리지 않는다.
        """
        self._catalog = catalog
        self._providers = dict(providers)
        self._calls = calls
        self._on_record_error = on_record_error

    def complete(self, request: ModelRequest) -> ModelResponse:
        """요청 하나를 보낸다. 한 번만 보낸다 — 실패는 ModelCallFailed 그대로 올라간다.

        보내기 전에 막는 것:
          대응표에 없거나 꺼진 이름  → UnknownModel · DisabledModel
          모델이 받지 않는 내용 종류  → UnsupportedInput
          저장된 파일 출처            → UnresolvedSource (FileStore 가 생기기 전까지)
          조립에 없는 공급자          → UnknownProvider
        """
        spec = resolve_model(self._catalog, request.model)
        check_inputs(request, spec)
        _reject_stored_sources(request)
        provider = self._providers.get(spec.provider)
        if provider is None:
            raise UnknownProvider(f"공급자 {spec.provider} 를 부를 수단이 없다")

        # 여기부터는 공급자에 보낸 호출이다 — 성공이든 실패든 한 줄 남긴다.
        started_at = datetime.now(UTC)
        started = time.monotonic()
        try:
            response = provider.complete(request, spec)
        except ModelCallFailed as error:
            self._record(
                _failed(request, spec, error.kind, error.detail, started_at, started)
            )
            raise

        # 구현의 「했다」를 그대로 믿지 않는다.
        # 보낸 요청의 응답인지 여기서 확인한다(E9).
        if response.request_id != request.request_id or response.model != request.model:
            mismatch = ProviderMismatch(
                f"요청({request.request_id}, {request.model})과 "
                f"응답({response.request_id}, {response.model})이 맞지 않는다"
            )
            # 보낸 것은 사실이라 남긴다. 응답의 숫자는 어느 요청의 것인지 믿을 수 없어
            # 남기지 않는다.
            self._record(
                _failed(request, spec, "unknown", str(mismatch), started_at, started)
            )
            raise mismatch

        self._record(_succeeded(request, response, started_at))
        return response

    def _record(self, record: CallRecord) -> None:
        try:
            self._calls.record(record)
        except Exception as error:  # noqa: BLE001 — 어떤 실패든 호출은 살린다
            self._on_record_error(record, error)


def _trace_fields(request: ModelRequest) -> dict:
    trace = request.trace
    if trace is None:
        return {}
    return {"run_id": trace.run_id, "step_id": trace.step_id, "attempt": trace.attempt}


def _succeeded(
    request: ModelRequest, response: ModelResponse, started_at: datetime
) -> CallRecord:
    return CallRecord(
        request_id=request.request_id,
        model=request.model,
        provider=response.provider,
        provider_model=response.provider_model,
        upstream_provider=response.upstream_provider,
        status="ok",
        finish_reason=response.finish_reason,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cost=response.usage.cost,
        latency_ms=response.latency_ms,
        started_at=started_at,
        **_trace_fields(request),
    )


def _failed(
    request: ModelRequest,
    spec: ModelSpec,
    kind: FailureKind,
    detail: str,
    started_at: datetime,
    started: float,
) -> CallRecord:
    return CallRecord(
        request_id=request.request_id,
        model=request.model,
        provider=spec.provider,
        provider_model=spec.provider_model,
        status="failed",
        failure_kind=kind,
        failure_detail=detail,
        # 실패는 어댑터가 잰 시간이 없어서 Gateway 가 잰다.
        latency_ms=int((time.monotonic() - started) * 1000),
        started_at=started_at,
        **_trace_fields(request),
    )


def _reject_stored_sources(request: ModelRequest) -> None:
    for message in request.messages:
        for part in message.content:
            if isinstance(part, ImagePart | FilePart) and isinstance(
                part.source, StoredSource
            ):
                raise UnresolvedSource(
                    f"저장된 파일({part.source.file_id})은 FileStore 가 생기기 전까지 "
                    "보낼 수 없다"
                )
