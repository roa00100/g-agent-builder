"""셸 — 켜 둔 채로 한 줄씩 받는다.

입력은 가짜(줄 목록)로 넣는다.
마지막 한 테스트는 실제 prompt_toolkit 을 파이프로 돌린다.
명령 실행(execute)과 연결 닫기(close_all)는 바꿔 끼워, 무엇이 불렸는지 본다.
"""

import json

import pytest
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from agent_builder_infra.observability import configure_logging
from agent_builder_runtime.__main__ import main
from agent_builder_runtime.cli import shell


class Lines:
    """줄을 차례로 돌려준다. 예외를 넣으면 그 자리에서 올린다. 다 쓰면 Ctrl-D."""

    def __init__(self, *items):
        self.items = list(items)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.items:
            raise EOFError
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture
def calls(monkeypatch):
    """execute·close_all 을 바꿔 끼우고 불린 것을 모은다."""
    seen = {"execute": [], "close_all": 0}

    def fake_execute(argv, **attributes):
        seen["execute"].append((argv, attributes))
        if argv and argv[0] == "boom":
            raise RuntimeError("뜻밖")
        if argv and argv[0] == "bad-args":
            raise SystemExit(2)
        return 0

    def fake_close_all():
        seen["close_all"] += 1

    monkeypatch.setattr(shell, "execute", fake_execute)
    monkeypatch.setattr(shell, "close_all", fake_close_all)
    return seen


def test_runs_commands_until_exit_and_closes_once(calls, capsys):
    code = shell.run_shell(
        "김재형",
        Lines(
            "/model calls --limit 3", '/model call fast "안 녕" --max-tokens 5', "/exit"
        ),
    )

    assert code == 0
    argvs = [argv for argv, _ in calls["execute"]]
    assert argvs == [
        ["model", "calls", "--limit", "3"],
        ["model", "call", "fast", "안 녕", "--max-tokens", "5"],
    ]
    # 연결은 끝날 때 한 번만 닫는다.
    assert calls["close_all"] == 1
    out = capsys.readouterr().out
    assert "사용자 김재형" in out


def test_every_command_carries_session_and_user(calls):
    shell.run_shell("김재형", Lines("/model calls", "/model calls"))

    (_, first), (_, second) = calls["execute"]
    assert first["user"] == "김재형"
    assert first["shell.session_id"] == second["shell.session_id"]


def test_plain_words_say_router_is_not_there_yet(calls, capsys):
    shell.run_shell("u", Lines("회의록 요약해 줘"))

    err = capsys.readouterr().err
    assert "진입점이 아직 없습니다" in err
    assert "'회의록 요약해 줘'" in err
    assert calls["execute"] == []


def test_failures_do_not_stop_the_shell(calls, capsys):
    shell.run_shell(
        "u",
        Lines(
            '/model call fast "닫히지 않은',  # 따옴표 오류
            "/bad-args",  # argparse 가 SystemExit
            "/boom",  # 예상하지 못한 오류
            KeyboardInterrupt(),  # Ctrl-C
            "",  # 빈 줄
            "/model calls",
        ),
    )

    err = capsys.readouterr().err
    assert "따옴표가 맞지 않습니다" in err
    assert "예상하지 못한 오류" in err
    assert "RuntimeError — 뜻밖" in err
    # 앞의 실패들 뒤에도 마지막 명령까지 갔다.
    assert calls["execute"][-1][0] == ["model", "calls"]
    assert calls["close_all"] == 1


def test_help_prints_commands(calls, capsys):
    shell.run_shell("u", Lines("/help"))

    out = capsys.readouterr().out
    assert "model-catalog" in out
    assert calls["execute"] == []


def test_asks_user_when_not_given(calls, capsys):
    reader = Lines("", "  김재형  ", "/exit")

    shell.run_shell(None, reader)

    assert reader.prompts[:2] == ["사용자 이름: ", "사용자 이름: "]
    assert "사용자 김재형" in capsys.readouterr().out


def test_ctrl_d_at_user_question_ends_without_starting(calls):
    assert shell.run_shell(None, Lines()) == 0
    assert calls["close_all"] == 0


def test_log_lines_carry_session_and_user(calls, capsys):
    configure_logging("INFO", "json")

    shell.run_shell("김재형", Lines("/exit"))

    lines = [
        json.loads(line)
        for line in capsys.readouterr().err.splitlines()
        if line.startswith("{")
    ]
    events = {line["event"]: line for line in lines}
    assert events["shell.start"]["user"] == "김재형"
    assert (
        events["shell.start"]["shell_session_id"]
        == events["shell.end"]["shell_session_id"]
    )


def test_main_without_command_opens_the_shell(monkeypatch):
    seen = []
    monkeypatch.setattr(shell, "run_shell", lambda user: seen.append(user) or 0)

    assert main(["--profile", "cli", "--user", "김재형"]) == 0
    assert seen == ["김재형"]


def test_completer_offers_groups_and_commands():
    from prompt_toolkit.document import Document

    completer = shell._completer()
    groups = {c.text for c in completer.get_completions(Document("/mo"), None)}
    commands = {c.text for c in completer.get_completions(Document("/model ca"), None)}

    assert {"/model", "/model-catalog", "/model-provider"} <= groups
    assert {"call", "calls", "call-show"} <= commands


def test_real_prompt_toolkit_reads_lines(tmp_path):
    with create_pipe_input() as pipe:
        read = shell._prompt_toolkit_reader(
            tmp_path / "history", input=pipe, output=DummyOutput()
        )
        pipe.send_text("/model calls\r")
        assert read("> ") == "/model calls"
        pipe.send_text("두 번째 줄\r")
        assert read("> ") == "두 번째 줄"

    # 지난 입력이 파일에 남는다(다음에 켜도 위 화살표로 다시 쓸 수 있게).
    assert "두 번째 줄" in (tmp_path / "history").read_text(encoding="utf-8")
