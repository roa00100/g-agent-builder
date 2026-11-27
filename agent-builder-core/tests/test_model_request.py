"""모델 요청 계약. 저장소·공급자 없이 모양과 규칙을 확인한다."""

import base64
from typing import get_args

import pytest
from pydantic import ValidationError

from agent_builder_core.contracts.model import (
    FilePart,
    ImagePart,
    InputKind,
    Message,
    ModelRequest,
    ModelSpec,
    StoredSource,
    TextPart,
    UnsupportedInput,
    check_inputs,
)

PNG = base64.b64encode(b"\x89PNG....").decode()


def request(**changes) -> ModelRequest:
    values = {
        "model": "fast",
        "messages": [{"role": "user", "content": "안녕"}],
        "params": {"max_output_tokens": 100},
    }
    return ModelRequest.model_validate({**values, **changes})


def spec(**changes) -> ModelSpec:
    values = {
        "name": "fast",
        "provider": "openrouter",
        "provider_model": "vendor/model-a",
        "input_kinds": ("text",),
    }
    return ModelSpec(**{**values, **changes})


# --- 조각 ---


def test_part_types_match_input_kinds():
    # 조각의 type 값과 InputKind 는 같은 세 낱말이어야 한다.
    part_types = {
        get_args(cls.model_fields["type"].annotation)[0]
        for cls in (TextPart, ImagePart, FilePart)
    }

    assert part_types == set(get_args(InputKind))


def test_string_shortcut_becomes_text_part():
    message = Message(role="user", content="안녕")

    assert message.content == (TextPart(text="안녕"),)


def test_image_part_with_each_source():
    for source in (
        {"type": "inline", "data": PNG},
        {"type": "url", "url": "https://example.com/a.png"},
        {"type": "stored", "file_id": "file-1"},
    ):
        part = ImagePart.model_validate({"source": source, "media_type": "image/png"})
        assert part.source.type == source["type"]


@pytest.mark.parametrize(
    "source",
    [
        {"type": "inline", "data": "not base64!"},
        {"type": "url", "url": "ftp://example.com/a.png"},
        {"type": "stored", "file_id": ""},
        {"type": "disk", "path": "/tmp/a.png"},
    ],
)
def test_bad_source_is_rejected(source):
    with pytest.raises(ValidationError):
        ImagePart.model_validate({"source": source, "media_type": "image/png"})


@pytest.mark.parametrize("media_type", ["png", "image", "image/", "/png", "image/ png"])
def test_media_type_must_be_type_slash_subtype(media_type):
    with pytest.raises(ValidationError):
        FilePart(source=StoredSource(file_id="f"), media_type=media_type)


# --- 메시지 ---


def test_user_can_send_text_image_file():
    message = Message.model_validate(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "이 문서 봐"},
                {
                    "type": "image",
                    "source": {"type": "inline", "data": PNG},
                    "media_type": "image/png",
                },
                {
                    "type": "file",
                    "source": {"type": "stored", "file_id": "f-1"},
                    "media_type": "application/pdf",
                    "filename": "a.pdf",
                },
            ],
        }
    )

    assert [part.type for part in message.content] == ["text", "image", "file"]


@pytest.mark.parametrize("role", ["assistant", "tool"])
def test_only_user_can_send_images(role):
    extra = {"tool_call_id": "c1"} if role == "tool" else {}
    with pytest.raises(ValidationError, match="담을 수 없는 내용"):
        Message.model_validate(
            {
                "role": role,
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "stored", "file_id": "f"},
                        "media_type": "image/png",
                    }
                ],
                **extra,
            }
        )


def test_empty_content_only_for_assistant_tool_call():
    call = {"id": "c1", "name": "search", "arguments": {"q": "x"}}

    assert Message(role="assistant", tool_calls=[call]).content == ()
    with pytest.raises(ValidationError, match="내용이 없다"):
        Message(role="user", content=[])
    with pytest.raises(ValidationError, match="내용이 없다"):
        Message(role="assistant")


def test_tool_calls_only_on_assistant():
    call = {"id": "c1", "name": "search", "arguments": {}}
    with pytest.raises(ValidationError, match="tool_calls"):
        Message(role="user", content="x", tool_calls=[call])


def test_tool_message_needs_tool_call_id_and_others_must_not_have_it():
    assert Message(role="tool", content="결과", tool_call_id="c1").tool_call_id == "c1"
    with pytest.raises(ValidationError, match="tool_call_id"):
        Message(role="tool", content="결과")
    with pytest.raises(ValidationError, match="tool_call_id"):
        Message(role="user", content="x", tool_call_id="c1")


# --- 요청 ---


def test_defaults():
    r = request()

    assert r.version == 1
    assert r.request_id
    assert r.request_id != request().request_id
    assert r.tool_choice == "auto"
    assert r.tools == ()


def test_envelope_rules():
    with pytest.raises(ValidationError):
        request(provider_options={"x": 1})
    with pytest.raises(ValidationError):
        request(version=2)
    with pytest.raises(ValidationError):
        request().model = "smart"


@pytest.mark.parametrize(
    "changes",
    [
        {"messages": []},
        {"model": ""},
        {"params": {}},
        {"params": {"max_output_tokens": 0}},
        {"params": {"max_output_tokens": 10, "temperature": -0.1}},
        {"params": {"max_output_tokens": 10, "top_p": 1.5}},
        {"trace": {"run_id": "r", "step_id": "s", "attempt": 0}},
    ],
)
def test_bad_request_shape(changes):
    with pytest.raises(ValidationError):
        request(**changes)


def test_tool_choice_rules():
    tool = {"name": "search", "description": "찾기", "parameters": {"type": "object"}}

    assert request(tools=[tool], tool_choice="search").tool_choice == "search"
    with pytest.raises(ValidationError, match="없는 도구"):
        request(tools=[tool], tool_choice="calc")
    with pytest.raises(ValidationError, match="required"):
        request(tool_choice="required")
    with pytest.raises(ValidationError, match="겹친다"):
        request(tools=[tool, tool])


def test_round_trip_through_json():
    # 기록해 둔 요청을 다시 읽어도 같아야 한다.
    original = request(
        system="짧게 답한다",
        trace={"run_id": "r1", "step_id": "s1", "attempt": 1},
        output={"name": "answer", "json_schema": {"type": "object"}},
    )

    assert ModelRequest.model_validate_json(original.model_dump_json()) == original


# --- 요청과 모델 ---


def test_check_inputs_passes_when_model_accepts_all_kinds():
    r = request(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "봐"},
                    {
                        "type": "image",
                        "source": {"type": "stored", "file_id": "f"},
                        "media_type": "image/png",
                    },
                ],
            }
        ]
    )

    assert r.input_kinds() == {"text", "image"}
    check_inputs(r, spec(input_kinds=("text", "image")))


def test_check_inputs_rejects_unsupported_kind():
    r = request(
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "file",
                        "source": {"type": "stored", "file_id": "f"},
                        "media_type": "application/pdf",
                    }
                ],
            }
        ]
    )

    with pytest.raises(UnsupportedInput, match="file"):
        check_inputs(r, spec())


def test_check_inputs_rejects_other_model():
    with pytest.raises(ValueError, match="다르다"):
        check_inputs(request(), spec(name="smart"))
