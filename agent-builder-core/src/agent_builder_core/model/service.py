"""모델 호출 서비스.

대응표 찾기, 맞는지 보기, 공급자 고르기, 보내기를 한 순서로 묶는다.

cli·rest·assist 는 이 서비스를 부르기만 한다. 공급자를 직접 고르지 않는다.
"""

from collections.abc import Mapping

from agent_builder_core.contracts.model import (
    ModelCatalog,
    ModelRequest,
    ModelResponse,
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


class ModelGateway:
    def __init__(
        self, catalog: ModelCatalog, providers: Mapping[str, ModelProvider]
    ) -> None:
        self._catalog = catalog
        self._providers = dict(providers)

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

        response = provider.complete(request, spec)

        # 구현의 「했다」를 그대로 믿지 않는다.
        # 보낸 요청의 응답인지 여기서 확인한다(E9).
        if response.request_id != request.request_id or response.model != request.model:
            raise ProviderMismatch(
                f"요청({request.request_id}, {request.model})과 "
                f"응답({response.request_id}, {response.model})이 맞지 않는다"
            )
        return response


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
