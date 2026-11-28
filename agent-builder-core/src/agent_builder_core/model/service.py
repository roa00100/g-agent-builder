"""모델 호출 서비스.

대응표 찾기, 맞는지 보기, 공급자 고르기, 보내기, 기록하기를 한 순서로 묶는다.

cli·rest·assist 는 이 서비스를 부르기만 한다. 공급자를 직접 고르지 않는다.
"""

import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from agent_builder_core.contracts.model import (
    BodyName,
    CallLog,
    CallNotRecorded,
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

    def __init__(self, file_ids: tuple[str, ...]) -> None:
        super().__init__(
            f"저장된 파일({', '.join(file_ids)})을 내용으로 바꾸는 기능(FileStore)이 "
            "아직 없다"
        )
        self.file_ids = file_ids


class ProviderMismatch(RuntimeError):
    """공급자가 돌려준 응답이 보낸 요청과 맞지 않는다 — 구현의 결함이다."""

    def __init__(self, request_id: str, detail: str) -> None:
        super().__init__(detail)
        self.request_id = request_id


class ModelGateway:
    def __init__(
        self,
        catalog: ModelCatalog,
        providers: Mapping[str, ModelProvider],
        calls: CallLog,
    ) -> None:
        self._catalog = catalog
        self._providers = dict(providers)
        self._calls = calls

    def complete(self, request: ModelRequest) -> ModelResponse:
        """요청 하나를 보낸다. 한 번만 보낸다 — 실패는 ModelCallFailed 그대로 올라간다.

        기록하지 못한 결과는 쓰지 않는다(추적 가능성 — 사용자 지시):
          요청 본문을 못 남기면 보내지 않는다         → CallNotRecorded(sent=False)
          보낸 뒤 본문·기록을 못 남기면 답을 버린다  → CallNotRecorded(sent=True)

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
            raise UnknownProvider(spec.provider, "not_assembled")

        # 여기부터는 공급자에 보내는 호출이다 — 성공이든 실패든 한 줄 남긴다.
        journal = _Journal(self._calls, request.request_id)
        journal.save(
            "request",
            {
                "request": request.model_dump(mode="json"),
                # 그때 쓴 대응표 줄의 사본 — 대응표를 나중에 고쳐도 남는다.
                "spec": spec.model_dump(mode="json"),
            },
        )
        started_at = datetime.now(UTC)
        started = time.monotonic()
        try:
            response = provider.complete(request, spec, journal)
        except ModelCallFailed as error:
            self._record(
                _failed(request, spec, error.kind, error.detail, started_at, started),
                journal,
            )
            raise
        except CallNotRecorded as error:
            # 공급자 구현 안에서 본문을 못 남겼다. 보낸 뒤라면 돈을 썼을 수 있으니
            # 숫자 없는 실패 줄이라도 남겨 본다. 그것마저 못 하면 원래 실패를 올린다.
            if error.sent:
                failed = _failed(
                    request, spec, "unknown", str(error), started_at, started
                )
                try:
                    self._calls.record(_with_bodies(failed, journal))
                except Exception:  # noqa: BLE001, S110 — 원래 실패가 더 중요하다
                    pass
            raise

        # 구현의 「했다」를 그대로 믿지 않는다.
        # 보낸 요청의 응답인지 여기서 확인한다(E9).
        if response.request_id != request.request_id or response.model != request.model:
            mismatch = ProviderMismatch(
                request.request_id,
                f"요청({request.request_id}, {request.model})과 "
                f"응답({response.request_id}, {response.model})이 맞지 않는다",
            )
            # 보낸 것은 사실이라 남긴다. 응답의 숫자는 어느 요청의 것인지 믿을 수 없어
            # 줄에는 넣지 않는다 — 받은 원문(received)이 본문으로 남아 있다.
            self._record(
                _failed(request, spec, "unknown", str(mismatch), started_at, started),
                journal,
            )
            raise mismatch

        journal.save("response", response.model_dump(mode="json"))
        self._record(_succeeded(request, response, started_at), journal)
        return response

    def _record(self, record: CallRecord, journal: "_Journal") -> None:
        try:
            self._calls.record(_with_bodies(record, journal))
        except Exception as error:
            # 기록 없는 결과는 쓰지 않는다 — 답을 받았어도 버린다.
            raise CallNotRecorded(
                record.request_id, "record", sent=True, detail=str(error)
            ) from error


class _Journal:
    """호출 하나의 본문을 남긴다. 공급자 구현에는 CallJournal 로 넘어간다.

    sending 을 남긴 뒤부터는 공급자에 보냈을 수 있다고 본다.
    """

    def __init__(self, calls: CallLog, request_id: str) -> None:
        self._calls = calls
        self._request_id = request_id
        self.keys: dict[BodyName, str] = {}
        self.sent = False

    def save(self, name: BodyName, content: dict[str, Any]) -> None:
        try:
            self.keys[name] = self._calls.save_body(self._request_id, name, content)
        except Exception as error:
            raise CallNotRecorded(
                self._request_id, name, sent=self.sent, detail=str(error)
            ) from error

    def sending(self, payload: dict[str, Any], settings: dict[str, Any]) -> None:
        self.save("sending", {"payload": payload, "settings": settings})
        self.sent = True

    def received(self, body: dict[str, Any]) -> None:
        self.save("received", body)


def _with_bodies(record: CallRecord, journal: _Journal) -> CallRecord:
    return record.model_copy(update={"bodies": dict(journal.keys)})


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
    file_ids = tuple(
        part.source.file_id
        for message in request.messages
        for part in message.content
        if isinstance(part, ImagePart | FilePart)
        and isinstance(part.source, StoredSource)
    )
    if file_ids:
        raise UnresolvedSource(file_ids)
