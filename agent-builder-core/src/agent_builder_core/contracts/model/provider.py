"""모델 공급자 계약 — 모델 요청을 공급자에게 보내고 응답을 받는다.

구현은 공급자마다 하나 (예: runtime 의 OpenRouterAdapter).
어느 공급자를 쓸지는 모델 대응표(ModelSpec.provider)가 정하고,
고르는 일은 ModelGateway 가 한다.
"""

from typing import Literal, Protocol, runtime_checkable

from agent_builder_core.contracts.model.catalog import ModelSpec
from agent_builder_core.contracts.model.record import CallJournal
from agent_builder_core.contracts.model.request import ModelRequest
from agent_builder_core.contracts.model.response import ModelResponse


@runtime_checkable
class ModelProvider(Protocol):
    # 공급자 이름. 대응표의 ModelSpec.provider 와 같은 값이다 (예: openrouter).
    name: str

    def complete(
        self, request: ModelRequest, spec: ModelSpec, journal: CallJournal
    ) -> ModelResponse:
        """요청을 spec 의 실제 모델(provider_model)로 한 번 보낸다.

        실패하면 ModelCallFailed. 다시 보내지 않는다.
        다시 보낼지는 부르는 쪽이 정한다(T3).

        journal: 보내기 직전에 sending(실제 본문, 그때의 설정), 받은 직후에
        received(받은 본문 그대로)를 부른다.
        journal 이 올리는 CallNotRecorded 는 잡지 않는다.
        """
        ...


# 공급자를 부를 수 없는 까닭.
#   no_profile     공급자 프로필(주소·키)이 없다
#   disabled       공급자 프로필을 꺼 두었다
#   not_assembled  이 프로그램에 그 공급자를 부르는 구현이 없다(조립에 빠졌다)
UnknownProviderReason = Literal["no_profile", "disabled", "not_assembled"]


class UnknownProvider(LookupError):
    """대응표가 가리키는 공급자를 부를 수 없다. 까닭은 reason 에 있다."""

    _TEXT = {
        "no_profile": "공급자 프로필 「{name}」 이 없다",
        "disabled": "공급자 「{name}」 은 프로필이 있지만 꺼져 있다",
        "not_assembled": "이 프로그램에 공급자 「{name}」 을 부르는 구현이 없다",
    }

    def __init__(self, name: str, reason: UnknownProviderReason) -> None:
        super().__init__(self._TEXT[reason].format(name=name))
        self.name = name
        self.reason: UnknownProviderReason = reason
