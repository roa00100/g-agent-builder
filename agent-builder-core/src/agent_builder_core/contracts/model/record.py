"""호출 기록 — 모델을 한 번 부를 때마다 남는 한 줄과 그 본문. 공급자·저장 기술을 모른다.

공급자에 보낸 호출만 남긴다(성공이든 ModelCallFailed 든). 보내기 전에 막힌 것은
돈도 시간도 쓰지 않았으므로 남기지 않는다.

추적 가능성은 절대 전제다(사용자 지시). 그래서
- 숫자는 기록 한 줄(CallRecord)에, 오간 본문은 따로 남기고 그 위치를 기록에 둔다.
- 기록하지 못한 결과는 쓰지 않는다 — 남기지 못하면 CallNotRecorded 로 호출을 멈춘다.

본문은 네 가지다. 앞의 둘은 보내기 전에 남긴다.
  request   계약의 말로 된 요청과, 그때 쓴 대응표 줄(ModelSpec)     — Gateway
  sending   공급자에 실제로 보낼 본문과, 그때의 공급자 설정(키 제외) — 공급자 구현
  received  공급자가 돌려준 본문 그대로 (오류 본문 포함)             — 공급자 구현
  response  계약의 말로 바꾼 응답 — 다음 칸으로 넘어간 것             — Gateway
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import Field, model_validator

from agent_builder_core.contracts.envelope import Envelope
from agent_builder_core.contracts.model.response import (
    FailureKind,
    FinishReason,
    is_retryable,
)

CallStatus = Literal["ok", "failed"]
BodyName = Literal["request", "sending", "received", "response"]


class CallRecord(Envelope):
    version: Literal[1] = 1
    # 요청의 request_id. 기록 하나에 요청 하나.
    request_id: str = Field(min_length=1)
    # 논리 이름과, 대응표가 고른 공급자·모델.
    model: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    # 성공이면 실제로 답한 모델(응답), 실패면 대응표의 모델.
    provider_model: str = Field(min_length=1)
    # 공급자 뒤에서 실제로 답한 곳 (OpenRouter 가 알려 주는 예: OpenAI). 모르면 비움.
    upstream_provider: str | None = None
    status: CallStatus
    # 성공일 때만.
    finish_reason: FinishReason | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    # 공급자가 알려 줄 때만. 단위는 공급자가 청구하는 통화(OpenRouter 는 크레딧).
    cost: Decimal | None = Field(default=None, ge=0)
    # 실패일 때만.
    failure_kind: FailureKind | None = None
    failure_detail: str | None = None
    # 성공이면 공급자에 보내고 받기까지(어댑터가 잼), 실패면 Gateway 가 잰 시간.
    latency_ms: int = Field(ge=0)
    # 보낸 시각. UTC.
    started_at: datetime
    # 요청에 실행 문맥(TraceContext)이 있으면 — 한 실행·한 단계의 비용을 묶는 열쇠.
    run_id: str | None = None
    step_id: str | None = None
    attempt: int | None = Field(default=None, ge=1)
    # 남긴 본문의 위치 — 이름 → 저장소 키. 남긴 것만 있다.
    bodies: dict[BodyName, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_status(self) -> "CallRecord":
        if self.started_at.tzinfo is None:
            raise ValueError("started_at 은 시간대가 있어야 한다 (UTC)")
        if self.status == "ok":
            if self.finish_reason is None or self.failure_kind is not None:
                raise ValueError(
                    "성공 기록에는 finish_reason 이 있고 failure_kind 가 없다"
                )
            if self.input_tokens is None or self.output_tokens is None:
                raise ValueError("성공 기록에는 토큰 수가 있다")
        elif self.failure_kind is None or self.finish_reason is not None:
            raise ValueError("실패 기록에는 failure_kind 가 있고 finish_reason 이 없다")
        return self

    @property
    def retryable(self) -> bool | None:
        """실패면 다시 보내 볼 만한지, 성공이면 None.

        failure_kind 에서 나오므로 따로 저장하지 않는다.
        """
        return None if self.failure_kind is None else is_retryable(self.failure_kind)


class CallNotRecorded(RuntimeError):
    """추적에 필요한 기록이나 본문을 남기지 못했다 — 그 결과는 쓰지 않는다.

    stage: 남기지 못한 것 (request·sending·received·response·record)
    sent: 공급자에 보냈을 수 있는가 — True 면 돈을 썼을 수 있다
    """

    def __init__(self, request_id: str, stage: str, sent: bool, detail: str) -> None:
        state = "보냈을 수 있음" if sent else "보내지 않음"
        super().__init__(
            f"[{stage} 를 남기지 못함, {state}] {detail} (request_id={request_id})"
        )
        self.request_id = request_id
        self.stage = stage
        self.sent = sent
        self.detail = detail


@runtime_checkable
class CallJournal(Protocol):
    """공급자 구현이 보내기 직전과 받은 직후에 본문을 남기는 곳.

    Gateway 가 호출마다 하나 만들어 넘긴다. 남기지 못하면 CallNotRecorded 를 올린다 —
    공급자 구현은 그것을 잡지 않고 그대로 올린다.
    """

    def sending(self, payload: dict[str, Any], settings: dict[str, Any]) -> None:
        """보내기 전에 부른다. 실패하면 보내지 않는다.

        settings: 그때의 공급자 설정 — 주소·대기 시간 등. 비밀(키)은 넣지 않는다.
        """
        ...

    def received(self, body: dict[str, Any]) -> None:
        """받은 본문을 바꾸기 전에 그대로 넘긴다. 오류 본문도 넘긴다."""
        ...


@runtime_checkable
class CallLog(Protocol):
    """호출 기록과 본문을 남기고 본다.

    고치거나 지우지 않는다 — 있었던 일의 기록이라서.
    """

    def record(self, record: CallRecord) -> None:
        """한 줄 남긴다. 실패하면 예외를 올린다.

        그때 어떻게 할지는 Gateway 가 정한다.
        """
        ...

    def save_body(self, request_id: str, name: BodyName, content: dict) -> str:
        """본문 하나를 남기고 위치(키)를 돌려준다. 실패하면 예외를 올린다."""
        ...

    def read_body(self, key: str) -> dict | None: ...

    def get(self, request_id: str) -> CallRecord | None: ...

    def list(self, limit: int) -> list[CallRecord]:
        """최근 것부터 limit 개."""
        ...
