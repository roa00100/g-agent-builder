"""모델 공급자 계약 — 모델 요청을 공급자에게 보내고 응답을 받는다.

구현은 공급자마다 하나 (예: runtime 의 OpenRouterModelProvider).
어느 공급자를 쓸지는 모델 대응표(ModelSpec.provider)가 정하고,
고르는 일은 ModelGateway 가 한다.
"""

from typing import Protocol, runtime_checkable

from agent_builder_core.contracts.model.catalog import ModelSpec
from agent_builder_core.contracts.model.request import ModelRequest
from agent_builder_core.contracts.model.response import ModelResponse


@runtime_checkable
class ModelProvider(Protocol):
    # 공급자 이름. 대응표의 ModelSpec.provider 와 같은 값이다 (예: openrouter).
    name: str

    def complete(self, request: ModelRequest, spec: ModelSpec) -> ModelResponse:
        """요청을 spec 의 실제 모델(provider_model)로 한 번 보낸다.

        실패하면 ModelCallFailed. 다시 보내지 않는다.
        다시 보낼지는 부르는 쪽이 정한다(T3).
        """
        ...


class UnknownProvider(LookupError):
    """대응표가 가리키는 공급자를 부를 수단이 없다(조립에 빠졌다)."""
