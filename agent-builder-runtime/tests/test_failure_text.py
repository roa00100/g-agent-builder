"""실패 문장 — 경우마다 사실(보냈나·비용·남은 것)과 할 일이 맞게 나오는지.

문장 전체를 박아 두지 않고, 경우를 가르는 사실과 할 일의 명령만 본다.
"""

import pytest
from pydantic import ValidationError

from agent_builder_core.contracts.model import (
    CallNotRecorded,
    DisabledModel,
    ModelCallFailed,
    ModelRequest,
    UnknownModel,
    UnknownProvider,
    UnsupportedInput,
)
from agent_builder_core.model import ProviderMismatch, UnresolvedSource
from agent_builder_infra.services import CipherError
from agent_builder_runtime.container import MissingMasterKey
from agent_builder_runtime.failure_text import (
    NOT_SENT,
    NOTHING_CHANGED,
    explain,
    invalid_option,
    no_call_body,
    no_call_record,
)
from agent_builder_runtime.repositories import MissingApiKey


def joined(explanation) -> str:
    return explanation.text()


# --- 보내기 전에 막힌 것: 보내지 않았고 비용이 없다 ---


@pytest.mark.parametrize(
    ("error", "says", "step"),
    [
        (UnknownModel("nosuch"), "「nosuch」", "model-catalog list"),
        (DisabledModel("fast"), "꺼져 있습니다", "model-catalog enable fast"),
        (
            UnknownProvider("openrouter", "no_profile"),
            "프로필 「openrouter」 이 없습니다",
            "model-provider set openrouter",
        ),
        (
            UnknownProvider("openrouter", "disabled"),
            "꺼져 있습니다",
            "model-provider enable openrouter",
        ),
        (
            UnknownProvider("other", "not_assembled"),
            "부르는 구현이 없습니다",
            "model-catalog list",
        ),
        (
            UnsupportedInput("fast", ("image",), ("text",)),
            "text 만 받는데, 요청에 image",
            "--inputs image,text",
        ),
        (UnresolvedSource(("f-1",)), "f-1", "inline"),
        (MissingApiKey("openrouter"), "API 키가 없습니다", "set-key openrouter"),
        (MissingMasterKey("x"), "SECRET_ENCRYPTION_KEY", "Fernet.generate_key"),
        (CipherError("x"), "풀지 못했습니다", "set-key"),
    ],
)
def test_blocked_before_sending_says_not_sent(error, says, step):
    explanation = explain(error, "call")

    assert explanation.message.startswith(("부르지 않았습니다", "모델 「"))
    assert says in joined(explanation)
    assert NOT_SENT in explanation.facts
    assert any(step in line for line in explanation.next)


def test_unknown_model_while_managing_changes_nothing():
    explanation = explain(UnknownModel("nosuch"), "manage")

    assert explanation.message == "대응표에 모델 이름 「nosuch」 이 없습니다."
    assert explanation.facts == (NOTHING_CHANGED,)


def test_invalid_input_lists_each_field_with_the_value():
    with pytest.raises(ValidationError) as raised:
        ModelRequest(
            model="fast",
            messages=[{"role": "user", "content": "x"}],
            params={"max_output_tokens": 0},
        )

    explanation = explain(raised.value, "call")

    assert explanation.message == "부르지 않았습니다 — 입력값이 모양에 맞지 않습니다."
    assert (
        "params.max_output_tokens: 0 보다 커야 합니다 (받은 값: 0)" in explanation.facts
    )
    assert any("model call --help" in step for step in explanation.next)
    assert NOT_SENT in explanation.facts


# --- 공급자에 보낸 뒤의 실패 ---


@pytest.mark.parametrize(
    ("kind", "title", "retry"),
    [
        ("timeout", "대기 시간 안에", "다시 보내 볼 만합니다"),
        ("rate_limited", "호출 한도", "다시 보내 볼 만합니다"),
        ("unavailable", "장애", "다시 보내 볼 만합니다"),
        ("invalid_request", "받지 않았습니다", "다시 보내도 같은 결과"),
        ("auth", "키", "다시 보내도 같은 결과"),
        ("unknown", "분류되지 않은", "다시 보내도 같은 결과"),
    ],
)
def test_call_failure_by_kind(kind, title, retry):
    explanation = explain(ModelCallFailed(kind, "req-1", "원문 설명"), "call")

    assert explanation.message.startswith("답을 받지 못했습니다")
    assert title in explanation.message
    assert "원인 — 원문 설명" in explanation.facts
    assert "호출 기록이 실패로 남았습니다." in explanation.facts
    assert any(retry in fact for fact in explanation.facts)
    assert any("model call-show req-1 --body" in step for step in explanation.next)


def test_call_failure_not_sent_says_so():
    error = ModelCallFailed("auth", "req-2", "키 없음", sent=False)

    assert NOT_SENT in explain(error, "call").facts


def test_timeout_says_reaching_is_uncertain():
    facts = explain(ModelCallFailed("timeout", "req-3", "느림"), "call").facts

    assert any("닿았는지는 확실하지 않습니다" in fact for fact in facts)


def test_http_failure_says_provider_answered():
    facts = explain(ModelCallFailed("invalid_request", "req-3", "400"), "call").facts

    assert "공급자에 보냈고, 공급자가 실패로 답했습니다." in facts


# --- 기록을 남기지 못함 ---


def test_not_recorded_before_sending():
    error = CallNotRecorded("req-4", "request", sent=False, detail="연결 안 됨")
    explanation = explain(error, "call")

    assert explanation.message == "호출하지 않았습니다 — 기록 저장소에 쓸 수 없습니다."
    assert NOT_SENT in explanation.facts
    assert "원인 — 연결 안 됨" in explanation.facts
    assert any("요청 본문" in fact for fact in explanation.facts)
    assert any("docker compose ps" in step for step in explanation.next)


def test_not_recorded_after_sending():
    error = CallNotRecorded("req-5", "response", sent=True, detail="연결 안 됨")
    explanation = explain(error, "call")

    assert explanation.message == "답을 받았지만 기록을 남기지 못해 쓰지 않았습니다."
    assert "공급자에 보냈으므로 비용이 들었을 수 있습니다." in explanation.facts
    assert NOT_SENT not in explanation.facts
    assert any("model call-show req-5" in step for step in explanation.next)


def test_provider_mismatch_is_a_program_defect():
    explanation = explain(ProviderMismatch("req-6", "맞지 않음"), "call")

    assert "결함" in joined(explanation)
    assert "비용이 들었을 수 있습니다" in joined(explanation)
    assert any("model call-show req-6 --body" in step for step in explanation.next)


# --- 그 밖 ---


def test_text_renders_message_facts_and_steps():
    text = explain(DisabledModel("fast"), "call").text().splitlines()

    assert text[0].startswith("모델 「fast」 을 부르지 않았습니다")
    assert text[1] == f"  - {NOT_SENT}"
    assert text[2] == "할 일:"
    assert text[3].startswith("  - 켜기:")


def test_as_dict_has_three_parts():
    assert set(explain(UnknownModel("x"), "call").as_dict()) == {
        "message",
        "facts",
        "next",
    }


def test_small_helpers():
    assert "받은 값: 0" in invalid_option("--limit", 0, "1 이상").facts[0]
    assert "「r-1」" in no_call_record("r-1").message
    assert "「received」" in no_call_body("r-1", "received").message


def test_unknown_error_keeps_the_original_text():
    explanation = explain(KeyError("뜻밖"), "call")

    assert "뜻밖" in explanation.message
    assert "KeyError" in explanation.facts[0]
