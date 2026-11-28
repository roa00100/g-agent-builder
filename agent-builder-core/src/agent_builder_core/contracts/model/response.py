"""모델 응답 — 모델이 무엇을 돌려줬는가. 공급자를 모른다.

공급자 어댑터(나중)가 각 공급자의 응답을 이 모양으로 바꾼다.
실패는 응답이 아니라 예외(ModelCallFailed)로 낸다 — 실패와 「결과 없음」을 가른다(T7).
"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from agent_builder_core.contracts.envelope import Envelope
from agent_builder_core.contracts.model.content import TextPart
from agent_builder_core.contracts.model.request import Message

# 왜 멈췄나. 공급자마다 말이 달라서 다섯 가지로 고정하고,
# 원래 값은 finish_detail 에 둔다.
#   stop: 스스로 끝냄
#   length: max_output_tokens 에 닿음
#   tool_calls: 도구를 부르려고 멈춤
#   content_filter: 공급자의 내용 정책으로 멈춤
#   other: 위에 없는 사유
FinishReason = Literal["stop", "length", "tool_calls", "content_filter", "other"]


class Usage(Envelope):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    # 공급자가 알려 줄 때만 (OpenRouter 는 준다). 단위는 공급자가 청구하는 통화.
    cost: Decimal | None = Field(default=None, ge=0)


class ModelResponse(Envelope):
    # 응답 모양의 버전. 요청과 같은 까닭으로 Literal 로 둔다.
    version: Literal[1] = 1
    # 어느 요청의 응답인가 — 요청과 판정 기록을 잇는다(T10).
    request_id: str = Field(min_length=1)
    # 논리 이름 (요청과 같다).
    model: str = Field(min_length=1)
    # 실제로 보낸 공급자.
    provider: str = Field(min_length=1)
    # 실제로 답한 모델. 공급자가 돌려준 이름이다.
    # 공급자 쪽에서 다른 모델로 넘겼으면 명세의 이름과 다를 수 있다.
    provider_model: str = Field(min_length=1)
    # 모델이 돌려준 말. 요청의 Message 를 그대로 써서, 대화에 바로 이어 붙일 수 있다.
    message: Message
    finish_reason: FinishReason
    # 공급자가 준 원래 종료 사유.
    finish_detail: str | None = None
    usage: Usage
    # 보내고 받기까지 걸린 시간. 어댑터가 잰다.
    latency_ms: int = Field(ge=0)
    # 공급자 뒤에서 실제로 답한 곳. 공급자가 알려 줄 때만
    # (OpenRouter 는 본문의 provider 로 준다, 예: OpenAI).
    upstream_provider: str | None = None

    @model_validator(mode="after")
    def _check_message(self) -> "ModelResponse":
        if self.message.role != "assistant":
            raise ValueError("응답의 message 는 assistant 여야 한다")
        if self.finish_reason == "tool_calls" and not self.message.tool_calls:
            raise ValueError("finish_reason 이 tool_calls 인데 도구 호출이 없다")
        return self

    def text(self) -> str:
        """응답 메시지의 텍스트 조각을 이어 붙인 것. 없으면 빈 문자열."""
        return "".join(
            part.text for part in self.message.content if isinstance(part, TextPart)
        )


FailureKind = Literal[
    "timeout",  # 정해 둔 시간 안에 답이 없었다
    "rate_limited",  # 공급자가 호출 한도를 넘었다고 했다
    "unavailable",  # 공급자 쪽 장애 (5xx 등)
    "invalid_request",  # 요청이 공급자에게 맞지 않았다 — 다시 보내도 같다
    "auth",  # 키가 없거나 틀렸다
    "unknown",  # 위에 없는 실패
]

# 다시 보내면 될 수도 있는 실패. 다시 보낼지·몇 번까지인지는 런타임이 정한다(T3).
_RETRYABLE: frozenset[FailureKind] = frozenset(
    {"timeout", "rate_limited", "unavailable"}
)


def is_retryable(kind: FailureKind) -> bool:
    """그 종류의 실패가 다시 보내 볼 만한가."""
    return kind in _RETRYABLE


class ModelCallFailed(Exception):
    """모델 호출이 응답을 돌려주지 못했다.

    공급자가 답을 돌려줬지만 내용 정책으로 멈춘 경우는 실패가 아니라
    finish_reason="content_filter" 인 응답이다.
    """

    def __init__(
        self, kind: FailureKind, request_id: str, detail: str, *, sent: bool = True
    ) -> None:
        """sent: 공급자에 닿았을 수 있는가.

        보내기 전에 막힌 것을 아는 쪽만 False 를 준다(키가 없음, 보낼 본문으로
        바꾸지 못함 등). 모르면 「닿았을 수 있다」가 사실이라 기본값이 True 다.
        """
        super().__init__(f"[{kind}] {detail} (request_id={request_id})")
        self.kind: FailureKind = kind
        self.request_id = request_id
        self.detail = detail
        self.sent = sent

    @property
    def retryable(self) -> bool:
        return is_retryable(self.kind)


def parse_output[M: BaseModel](response: ModelResponse, model: type[M]) -> M:
    """응답 텍스트를 원하는 모양(요청의 output 에 적은 그 모델)으로 읽는다.

    모양이 다르면 ValidationError — 모델의 「됐다」를 믿지 않고 여기서 확인한다(E9, T7).
    """
    return model.model_validate_json(response.text())
