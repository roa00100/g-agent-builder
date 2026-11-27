"""모델 대응표의 계약 — 논리 이름 하나가 무엇을 약속하는가, 그것을 어떻게 찾고 고치는가.

어디에 저장하는지는 모른다. 구현은 infra 가 채운다.
누가 부를 수 있는가(권한)는 이 계약이 다루지 않는다. 필요해지면 부르는 쪽에서 정한다.
"""

from typing import Protocol, runtime_checkable

from pydantic import Field

from agent_builder_core.contracts.envelope import Envelope
from agent_builder_core.contracts.model.content import InputKind
from agent_builder_core.contracts.model.request import ModelRequest


class ModelSpec(Envelope):
    """논리 이름 하나가 약속하는 것."""

    # 논리 이름 (예: fast, smart). 모델 요청의 model 에 적는 값이다.
    name: str = Field(min_length=1)
    # 공급자 (예: openrouter). 어느 공급자 어댑터로 보낼지 정한다.
    provider: str = Field(min_length=1)
    # 공급자 쪽 실제 모델 이름.
    provider_model: str = Field(min_length=1)
    # 이 모델이 받는 내용 종류. 하나 이상.
    input_kinds: tuple[InputKind, ...] = Field(min_length=1)
    # 끄면 이 이름으로 오는 요청을 거부한다. 지우지 않고 끌 수 있게 둔다.
    enabled: bool = True
    # 이 모델만 다르게 기다릴 시간(초) — 생각이 긴 모델 등.
    # 비우면 공급자 프로필의 기본값을 쓴다.
    timeout_seconds: float | None = Field(default=None, gt=0)


class UnknownModel(LookupError):
    """대응표에 없는 논리 이름. 기본 모델로 넘기지 않는다."""


class DisabledModel(LookupError):
    """대응표에 있지만 꺼 둔 논리 이름."""


class UnsupportedInput(ValueError):
    """모델이 받지 않는 내용 종류가 요청에 들어 있다. 몰래 빼지 않는다."""


@runtime_checkable
class ModelCatalog(Protocol):
    """모델 대응표. 찾기와 고치기를 함께 둔다."""

    def get(self, name: str) -> ModelSpec | None:
        """한 줄. 없으면 None. 꺼 둔 줄도 돌려준다(enabled=False)."""
        ...

    def list(self) -> list[ModelSpec]:
        """전부, 이름 순."""
        ...

    def upsert(self, spec: ModelSpec) -> None:
        """이름이 없으면 넣고, 있으면 바꾼다."""
        ...

    def set_enabled(self, name: str, enabled: bool) -> None:
        """켜거나 끈다. 없는 이름이면 UnknownModel."""
        ...

    def delete(self, name: str) -> bool:
        """지웠으면 True, 없었으면 False."""
        ...


def resolve_model(catalog: ModelCatalog, name: str) -> ModelSpec:
    """모델 요청에 쓸 한 줄. 없으면 UnknownModel, 꺼져 있으면 DisabledModel."""
    spec = catalog.get(name)
    if spec is None:
        raise UnknownModel(f"대응표에 없는 모델 이름: {name}")
    if not spec.enabled:
        raise DisabledModel(f"꺼 둔 모델 이름: {name}")
    return spec


def check_inputs(request: ModelRequest, spec: ModelSpec) -> None:
    """요청이 그 모델에 맞는지 본다.

    요청의 model 과 명세의 이름이 다르면 ValueError,
    모델이 받지 않는 내용 종류가 있으면 UnsupportedInput.
    """
    if request.model != spec.name:
        raise ValueError(f"요청의 모델({request.model})과 명세({spec.name})가 다르다")
    unsupported = request.input_kinds() - set(spec.input_kinds)
    if unsupported:
        raise UnsupportedInput(
            f"모델 {spec.name} 이 받지 않는 내용: {sorted(unsupported)}"
        )
