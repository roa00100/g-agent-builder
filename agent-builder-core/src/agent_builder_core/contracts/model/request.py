"""모델 요청 — 모델 하나에게 무엇을 물을지. 공급자를 모른다.

공급자 어댑터(나중)가 이것을 각 공급자의 요청 모양으로 바꾼다.
공급자 전용 옵션 칸은 두지 않는다. 필요해지면 공통 필드로 올릴지 그때 정한다.
"""

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, field_validator, model_validator

from agent_builder_core.contracts.envelope import Envelope
from agent_builder_core.contracts.model.content import ContentPart, InputKind

Role = Literal["user", "assistant", "tool"]

ToolChoice = Literal["auto", "none", "required"] | str

# 역할마다 담을 수 있는 내용 종류. 모델이 돌려주는 말(assistant)과 도구 결과(tool)는
# 아직 텍스트만 받는다.
_ALLOWED_KINDS: dict[Role, frozenset[InputKind]] = {
    "user": frozenset({"text", "image", "file"}),
    "assistant": frozenset({"text"}),
    "tool": frozenset({"text"}),
}


class ToolCall(Envelope):
    """모델이 도구를 부른 한 번."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any]


class ToolSpec(Envelope):
    """모델이 부를 수 있는 도구 하나."""

    name: str = Field(min_length=1)
    # 모델이 언제 쓸지 판단하는 설명.
    description: str = Field(min_length=1)
    # 인자의 JSON 스키마.
    parameters: dict[str, Any]


class OutputSpec(Envelope):
    """원하는 응답 모양. 보통 Pydantic 모델의 model_json_schema() 로 만든다.

    검증은 요청이 아니라 응답을 받은 쪽이 같은 모델로 다시 읽어서 한다(T7).
    """

    name: str = Field(min_length=1)
    json_schema: dict[str, Any]


class GenerationParams(Envelope):
    # 응답 길이 상한. 기본값을 두지 않는다 — 부르는 쪽이 매번 정한다(E18).
    max_output_tokens: int = Field(gt=0)
    # 무작위성. 없으면 공급자 기본값. 상한은 공급자마다 달라(1 또는 2) 아래쪽만 막는다.
    temperature: float | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0, le=1)
    # 여기서 생성을 멈출 문자열.
    stop: tuple[str, ...] = ()
    # 재현용. 지원하는 공급자에서만 쓰인다.
    seed: int | None = None


class TraceContext(Envelope):
    """어느 실행의 어느 단계에서 나온 요청인가(T10)."""

    run_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    # 그 단계 고리의 몇 번째 판정인가. 1부터.
    attempt: int = Field(ge=1)


class Message(Envelope):
    role: Role
    # 문자열을 주면 텍스트 조각 하나로 바꿔 받는다.
    content: tuple[ContentPart, ...] = ()
    # assistant 가 도구를 부른 경우 그 호출들.
    tool_calls: tuple[ToolCall, ...] = ()
    # tool 이면 필수 — 어떤 도구 호출에 대한 결과인가.
    tool_call_id: str | None = None

    @field_validator("content", mode="before")
    @classmethod
    def _text_shortcut(cls, value: Any) -> Any:
        if isinstance(value, str):
            return ({"type": "text", "text": value},)
        return value

    @model_validator(mode="after")
    def _check_shape(self) -> "Message":
        # 도구만 부르고 말은 없는 assistant 메시지만 내용이 비어도 된다.
        if not self.content and not (self.role == "assistant" and self.tool_calls):
            raise ValueError(f"{self.role} 메시지에 내용이 없다")
        disallowed = {part.type for part in self.content} - _ALLOWED_KINDS[self.role]
        if disallowed:
            raise ValueError(
                f"{self.role} 메시지에 담을 수 없는 내용: {sorted(disallowed)}"
            )
        if self.tool_calls and self.role != "assistant":
            raise ValueError("tool_calls 는 assistant 메시지에만 둔다")
        if (self.role == "tool") != (self.tool_call_id is not None):
            raise ValueError("tool_call_id 는 tool 메시지에만, 그리고 반드시 둔다")
        return self


class ModelRequest(Envelope):
    # 요청 모양의 버전. 기록해 둔 요청을 다시 읽을 때, 모양이 바뀐 뒤의 기록을
    # 옛 클래스로 조용히 읽지 않도록 Literal 로 둔다.
    version: Literal[1] = 1
    # 이 요청의 ID. 응답과 판정 기록을 잇는 키(T10).
    request_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    # 논리 이름 (예: fast). ModelCatalog 로 공급자와 실제 모델을 찾는다.
    model: str = Field(min_length=1)
    # 시스템 지침. 공급자마다 넣는 자리가 달라 대화 메시지와 따로 둔다.
    system: str | None = None
    messages: tuple[Message, ...] = Field(min_length=1)
    params: GenerationParams
    output: OutputSpec | None = None
    tools: tuple[ToolSpec, ...] = ()
    # auto·none·required, 또는 tools 안의 도구 이름 하나.
    tool_choice: ToolChoice = "auto"
    trace: TraceContext | None = None

    @model_validator(mode="after")
    def _check_tools(self) -> "ModelRequest":
        names = [tool.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ValueError(f"도구 이름이 겹친다: {names}")
        if self.tool_choice == "required" and not self.tools:
            raise ValueError("tool_choice 가 required 인데 tools 가 비어 있다")
        if self.tool_choice not in ("auto", "none", "required") and (
            self.tool_choice not in names
        ):
            raise ValueError(f"tools 에 없는 도구를 골랐다: {self.tool_choice}")
        return self

    def input_kinds(self) -> frozenset[InputKind]:
        """이 요청의 메시지들이 담은 내용 종류."""
        return frozenset(
            part.type for message in self.messages for part in message.content
        )
