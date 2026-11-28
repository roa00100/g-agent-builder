"""실패를 사람이 읽는 문장으로 — 명령줄과 REST 가 같이 쓴다.

한 실패마다 세 가지를 사실대로 적는다.
  message  무엇을 했고(또는 하지 않았고) 왜인가 — 한 줄
  facts    보냈는가·비용이 들었을 수 있는가·무엇이 남았는가·원인
  next     다음에 할 일 — 실제로 있는 명령으로

추측은 「~일 수 있다」로만 쓴다. 기계가 읽는 이름(REST 의 kind, 로그 이벤트)은 여기서
바꾸지 않는다 — 이 모듈은 사람이 읽는 글만 만든다.
"""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import ValidationError

from agent_builder_core.contracts.model import (
    CallNotRecorded,
    DisabledModel,
    FailureKind,
    ModelCallFailed,
    UnknownModel,
    UnknownProvider,
    UnsupportedInput,
)
from agent_builder_core.model import ProviderMismatch, UnresolvedSource
from agent_builder_infra.services import CipherError
from agent_builder_runtime.container import MissingMasterKey
from agent_builder_runtime.repositories import MissingApiKey

# call: 모델을 부르다 난 실패 / manage: 대응표·공급자 프로필을 보거나 고치다 난 실패
During = Literal["call", "manage"]

CLI = "python -m agent_builder_runtime"

NOT_SENT = "공급자에 보내지 않았습니다. 비용은 들지 않았습니다."
NOTHING_CHANGED = "아무것도 바꾸지 않았습니다."

_STAGE = {
    "request": "요청 본문(보낸 말과 그때의 대응표 줄)",
    "sending": "공급자에 보낼 본문과 그때의 공급자 설정",
    "received": "공급자가 돌려준 본문",
    "response": "다음으로 넘길 응답 본문",
    "record": "호출 기록 한 줄",
}

_NO_ANSWER = "답을 받지 못했습니다 — "
_FAILED_TITLE: dict[FailureKind, str] = {
    "timeout": _NO_ANSWER + "공급자가 정해 둔 대기 시간 안에 답하지 않았습니다.",
    "rate_limited": _NO_ANSWER + "공급자가 호출 한도를 넘었다고 답했습니다.",
    "unavailable": _NO_ANSWER + "공급자 쪽 장애이거나 공급자에 연결하지 못했습니다.",
    "invalid_request": _NO_ANSWER + "공급자가 이 요청을 받지 않았습니다.",
    "auth": _NO_ANSWER + "공급자 API 키가 없거나 공급자가 키를 거부했습니다.",
    "unknown": _NO_ANSWER + "공급자가 분류되지 않은 오류를 돌려줬습니다.",
}

_FAILED_NEXT: dict[FailureKind, str] = {
    "timeout": (
        f"대기 시간 늘리기 — 이 모델만: {CLI} model-catalog set <모델> --provider "
        f"<공급자> --model <공급자 쪽 이름> --timeout <초>, 공급자 기본값: {CLI} "
        "model-provider set <공급자> --base-url <주소> --timeout <초>"
    ),
    "rate_limited": "잠시 뒤 같은 명령을 다시 실행합니다.",
    "unavailable": (
        f"잠시 뒤 다시 실행합니다. 계속되면 공급자 주소를 확인합니다: {CLI} "
        "model-provider show <공급자>"
    ),
    "invalid_request": (
        "받은 오류 원문을 보고, 보낸 내용이나 대응표의 공급자 쪽 모델 이름을 고칩니다: "
        f"{CLI} model-catalog list"
    ),
    "auth": f"키 넣기: {CLI} model-provider set-key <공급자>",
    "unknown": "받은 오류 원문을 확인합니다 (예: 크레딧 부족은 HTTP 402 로 옵니다).",
}


@dataclass(frozen=True)
class Explanation:
    message: str
    facts: tuple[str, ...] = field(default=())
    next: tuple[str, ...] = field(default=())

    def text(self) -> str:
        """명령줄에 찍는 여러 줄."""
        lines = [self.message]
        lines += [f"  - {fact}" for fact in self.facts]
        if self.next:
            lines.append("할 일:")
            lines += [f"  - {step}" for step in self.next]
        return "\n".join(lines)

    def as_dict(self) -> dict:
        """REST 응답 본문에 넣는 모양."""
        return {
            "message": self.message,
            "facts": list(self.facts),
            "next": list(self.next),
        }


def explain(error: Exception, during: During) -> Explanation:
    """알려진 실패를 문장으로. 모르는 실패도 원문을 그대로 담아 돌려준다."""
    if isinstance(error, UnknownModel):
        return _unknown_model(error, during)
    if isinstance(error, DisabledModel):
        return Explanation(
            f"모델 「{error.name}」 을 부르지 않았습니다 — "
            "대응표에 있지만 꺼져 있습니다.",
            (NOT_SENT,),
            (f"켜기: {CLI} model-catalog enable {error.name}",),
        )
    if isinstance(error, UnknownProvider):
        return _unknown_provider(error, during)
    if isinstance(error, UnsupportedInput):
        return _unsupported_input(error)
    if isinstance(error, UnresolvedSource):
        return Explanation(
            "부르지 않았습니다 — 요청에 저장된 파일("
            f"{', '.join(error.file_ids)})이 있는데, 저장된 파일을 내용으로 바꾸는 "
            "기능(FileStore)이 아직 없습니다.",
            (NOT_SENT,),
            ("파일 내용을 요청에 직접(inline, base64) 넣어 다시 보냅니다.",),
        )
    if isinstance(error, ValidationError):
        return _invalid_input(error, during)
    if isinstance(error, ModelCallFailed):
        return _call_failed(error)
    if isinstance(error, CallNotRecorded):
        return _not_recorded(error)
    if isinstance(error, ProviderMismatch):
        return _mismatch(error)
    if isinstance(error, MissingMasterKey):
        return _missing_master_key(during)
    if isinstance(error, CipherError):
        return Explanation(
            f"{_verb(during)} — 저장된 공급자 API 키를 풀지 못했습니다.",
            (
                "지금의 마스터 키(SECRET_ENCRYPTION_KEY)가 키를 넣을 때 쓴 것과 "
                "다를 수 있습니다.",
                NOT_SENT if during == "call" else NOTHING_CHANGED,
            ),
            (
                ".env 의 SECRET_ENCRYPTION_KEY 를 키를 넣을 때의 값으로 되돌리거나, "
                f"키를 다시 넣습니다: {CLI} model-provider set-key <공급자>",
            ),
        )
    if isinstance(error, MissingApiKey):
        return Explanation(
            f"{_verb(during)} — 공급자 「{error.provider}」 의 프로필에 API 키가 "
            "없습니다.",
            (NOT_SENT if during == "call" else NOTHING_CHANGED,),
            (f"키 넣기: {CLI} model-provider set-key {error.provider}",),
        )
    return Explanation(
        f"{_verb(during)} — {error}",
        (f"실패 종류: {type(error).__name__}",),
    )


def invalid_option(option: str, value: object, rule: str) -> Explanation:
    """명령줄 인자 하나가 규칙에 맞지 않을 때."""
    return Explanation(
        f"실행하지 않았습니다 — {option} 값이 맞지 않습니다.",
        (f"받은 값: {value!r}. {rule}", NOTHING_CHANGED),
        (f"값을 고쳐 다시 실행합니다. 도움말: {CLI} model --help",),
    )


def no_router_yet(text: str) -> Explanation:
    """셸에 말을 쳤는데 진입점(고르기)이 아직 없을 때."""
    return Explanation(
        "실행하지 않았습니다 — 말로 조립을 고르는 진입점이 아직 없습니다.",
        (f"받은 말: {text!r}", NOT_SENT),
        (
            '명령은 / 로 시작합니다: /model call fast "할 말" --max-tokens 200',
            "명령 목록: /help",
        ),
    )


def shell_bad_quotes(text: str, detail: str) -> Explanation:
    return Explanation(
        "실행하지 않았습니다 — 명령의 따옴표가 맞지 않습니다.",
        (f"받은 명령: /{text}", f"원인 — {detail}", NOTHING_CHANGED),
        ('따옴표를 닫아 다시 칩니다. 예: /model call fast "할 말" --max-tokens 200',),
    )


def shell_unexpected(text: str, error: Exception) -> Explanation:
    """셸에서 한 명령이 예상하지 못한 오류로 끝났을 때. 셸은 계속 켜져 있다."""
    return Explanation(
        "명령을 끝내지 못했습니다 — 예상하지 못한 오류가 났습니다.",
        (
            f"받은 명령: /{text}",
            f"오류: {type(error).__name__} — {error}",
            "어디까지 했는지는 알 수 없습니다. 셸은 계속 켜져 있습니다.",
        ),
        (
            "/exit 로 끝낸 뒤 같은 명령을 한 번 하고 끝나는 방식으로 실행하면 "
            f"자세한 내용(트레이스백)이 보입니다: {CLI} <묶음> <명령>",
        ),
    )


def no_call_record(request_id: str) -> Explanation:
    return Explanation(
        f"호출 기록 「{request_id}」 이 없습니다.",
        (
            "보내기 전에 막힌 호출(없는 모델·꺼진 모델·받지 않는 내용 등)은 기록되지 "
            "않습니다.",
        ),
        (f"최근 기록 보기: {CLI} model calls",),
    )


def no_call_body(request_id: str, name: str) -> Explanation:
    return Explanation(
        f"호출 「{request_id}」 의 본문 「{name}」 이 없습니다.",
        (
            "기록이 없거나, 그 호출이 그 단계까지 가지 않았습니다 (예: 보내기 전에 "
            "실패하면 received·response 가 없습니다).",
        ),
        (f"남은 본문 보기: {CLI} model call-show {request_id}",),
    )


# --- 경우별 ---


def _verb(during: During) -> str:
    return "부르지 않았습니다" if during == "call" else "바꾸지 않았습니다"


def _unknown_model(error: UnknownModel, during: During) -> Explanation:
    look = f"등록된 이름 보기: {CLI} model-catalog list"
    if during == "manage":
        return Explanation(
            f"대응표에 모델 이름 「{error.name}」 이 없습니다.",
            (NOTHING_CHANGED,),
            (look,),
        )
    return Explanation(
        f"모델 「{error.name}」 을 부르지 않았습니다 — 대응표에 그 이름이 없습니다.",
        (NOT_SENT, "보내기 전에 막혀 호출 기록도 남지 않았습니다."),
        (
            look,
            f"새로 넣기: {CLI} model-catalog set {error.name} --provider <공급자> "
            "--model <공급자 쪽 모델 이름>",
        ),
    )


def _unknown_provider(error: UnknownProvider, during: During) -> Explanation:
    name = error.name
    if error.reason == "no_profile":
        message = f"공급자 프로필 「{name}」 이 없습니다."
        steps = (
            f"프로필 넣기: {CLI} model-provider set {name} --base-url <주소> "
            "--timeout <초>",
            f"키 넣기: {CLI} model-provider set-key {name}",
        )
        facts = (
            "모델 대응표가 이 공급자를 가리키지만, 주소와 키를 담은 프로필이 없습니다.",
        )
    elif error.reason == "disabled":
        message = f"공급자 「{name}」 이 꺼져 있습니다."
        steps = (f"켜기: {CLI} model-provider enable {name}",)
        facts = ("공급자 프로필은 있지만 꺼 둔 상태라 이 공급자로 보내지 않습니다.",)
    else:
        message = f"이 프로그램에 공급자 「{name}」 을 부르는 구현이 없습니다."
        steps = (
            f"대응표의 공급자 칸 확인: {CLI} model-catalog list",
            f"고치기: {CLI} model-catalog set <모델> --provider <구현이 있는 공급자> "
            "--model <공급자 쪽 이름>",
        )
        facts = ("모델 대응표의 공급자 이름이 이 프로그램이 아는 공급자와 다릅니다.",)
    if during == "call":
        return Explanation(f"부르지 않았습니다 — {message}", (*facts, NOT_SENT), steps)
    return Explanation(message, (NOTHING_CHANGED,), steps)


def _unsupported_input(error: UnsupportedInput) -> Explanation:
    widened = ",".join(sorted({*error.accepted, *error.unsupported}))
    return Explanation(
        f"모델 「{error.model}」 을 부르지 않았습니다 — 이 모델은 "
        f"{', '.join(error.accepted)} 만 받는데, 요청에 {', '.join(error.unsupported)} "
        "이 들어 있습니다.",
        (NOT_SENT, "몰래 빼고 보내지 않습니다 — 빼면 받은 말과 보낸 말이 달라집니다."),
        (
            "그 내용을 받는 다른 모델 이름으로 부릅니다.",
            "이 모델이 실제로 그 내용을 받는다면 대응표를 고칩니다: "
            f"{CLI} model-catalog set {error.model} --provider <공급자> "
            f"--model <공급자 쪽 이름> --inputs {widened}",
        ),
    )


# Pydantic 의 검사 종류 → 한국어 문장. 여기 없는 종류는 Pydantic 의 원문을 그대로 쓴다.
_RULES: dict[str, str] = {
    "greater_than": "{gt} 보다 커야 합니다",
    "greater_than_equal": "{ge} 이상이어야 합니다",
    "less_than": "{lt} 보다 작아야 합니다",
    "less_than_equal": "{le} 이하여야 합니다",
    "missing": "꼭 있어야 합니다",
    "string_too_short": "{min_length} 글자 이상이어야 합니다",
    "extra_forbidden": "모르는 칸입니다",
    "literal_error": "다음 중 하나여야 합니다: {expected}",
    "int_parsing": "정수여야 합니다",
    "int_type": "정수여야 합니다",
}


def _rule(item: dict) -> str:
    template = _RULES.get(item["type"])
    if template is not None:
        try:
            return template.format(**(item.get("ctx") or {}))
        except KeyError:
            pass
    # 우리 계약의 검사(ValueError)는 이미 한국어다 — Pydantic 이 붙인 머리말만 뗀다.
    return str(item["msg"]).removeprefix("Value error, ")


def _invalid_input(error: ValidationError, during: During) -> Explanation:
    facts = []
    for item in error.errors():
        where = ".".join(str(part) for part in item["loc"]) or "(전체)"
        facts.append(f"{where}: {_rule(item)} (받은 값: {item.get('input')!r})")
    facts.append(NOT_SENT if during == "call" else NOTHING_CHANGED)
    help_for = "model call" if during == "call" else "<묶음> <명령>"
    return Explanation(
        f"{_verb(during)} — 입력값이 모양에 맞지 않습니다.",
        tuple(facts),
        (f"값을 고쳐 다시 실행합니다. 도움말: {CLI} {help_for} --help",),
    )


# 연결이 끊겼거나 답이 없었던 실패 — 공급자에 닿았는지 확실하지 않다.
# 그 밖의 종류는 공급자가 실패로 답한 것이라 닿았다.
_MAYBE_REACHED: frozenset[FailureKind] = frozenset({"timeout", "unavailable"})


def _sent_fact(error: ModelCallFailed) -> str:
    if not error.sent:
        return NOT_SENT
    if error.kind in _MAYBE_REACHED:
        return (
            "공급자에 보냈지만, 연결이 끊겼거나 답이 없어 공급자에 닿았는지는 "
            "확실하지 않습니다."
        )
    return "공급자에 보냈고, 공급자가 실패로 답했습니다."


def _call_failed(error: ModelCallFailed) -> Explanation:
    facts = [
        _sent_fact(error),
        f"원인 — {error.detail}",
        "호출 기록이 실패로 남았습니다.",
        "같은 요청을 다시 보내 볼 만합니다."
        if error.retryable
        else "같은 요청은 다시 보내도 같은 결과일 것입니다 — 먼저 원인을 고칩니다.",
    ]
    return Explanation(
        _FAILED_TITLE[error.kind],
        tuple(facts),
        (
            _FAILED_NEXT[error.kind],
            f"받은 오류 원문과 보낸 본문 보기: {CLI} model call-show "
            f"{error.request_id} --body",
        ),
    )


def _not_recorded(error: CallNotRecorded) -> Explanation:
    stage = _STAGE.get(error.stage, error.stage)
    check = (
        "저장소(Postgres·오브젝트 스토리지)가 떠 있는지 확인합니다: docker compose ps"
    )
    if not error.sent:
        return Explanation(
            "호출하지 않았습니다 — 기록 저장소에 쓸 수 없습니다.",
            (
                f"남기지 못한 것: {stage}",
                f"원인 — {error.detail}",
                NOT_SENT,
                "추적할 수 없는 호출은 하지 않습니다.",
            ),
            (check, "저장소를 확인한 뒤 같은 명령을 다시 실행합니다."),
        )
    return Explanation(
        "답을 받았지만 기록을 남기지 못해 쓰지 않았습니다.",
        (
            f"남기지 못한 것: {stage}",
            f"원인 — {error.detail}",
            "공급자에 보냈으므로 비용이 들었을 수 있습니다.",
            "추적할 수 없는 답은 다음으로 넘기지 않습니다.",
        ),
        (
            check,
            f"이 호출이 기록에 남았는지 보기: {CLI} model call-show {error.request_id}",
            "저장소를 확인한 뒤 같은 명령을 다시 실행합니다.",
        ),
    )


def _mismatch(error: ProviderMismatch) -> Explanation:
    return Explanation(
        "답을 쓰지 않았습니다 — 공급자 구현이 돌려준 응답이 보낸 요청과 맞지 않습니다.",
        (
            f"내용 — {error}",
            "공급자에 보냈으므로 비용이 들었을 수 있습니다.",
            "호출 기록이 실패(unknown)로 남았고, 받은 원문도 남았습니다.",
            "이것은 프로그램(공급자 구현)의 결함입니다.",
        ),
        (
            f"받은 원문 보기: {CLI} model call-show {error.request_id} --body",
            "공급자 구현(model_adapters)의 응답 바꾸기를 확인합니다.",
        ),
    )


def _missing_master_key(during: During) -> Explanation:
    return Explanation(
        f"{_verb(during)} — 마스터 키(SECRET_ENCRYPTION_KEY)가 설정되어 있지 않습니다.",
        (
            "공급자 API 키는 이 마스터 키로 암호화해 두므로, 키를 넣거나 풀 때 꼭 "
            "필요합니다.",
            NOT_SENT if during == "call" else NOTHING_CHANGED,
        ),
        (
            '만들기: python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"',
            "만든 값을 .env 의 SECRET_ENCRYPTION_KEY= 에 적고 다시 실행합니다.",
        ),
    )
