"""셸 — cli 모드를 켜 둔 채로 계속 받는다.

python -m agent_builder_runtime --user 김재형     (명령 없이 실행하면 셸이 뜬다)

  /로 시작   지금의 명령 그대로 — /model call fast "안녕" --max-tokens 50
  그냥 말    진입점(고르기)으로 간다 — 고르기가 생기기 전까지는 「아직 없다」고 답한다
  /help      명령 목록
  /exit · /quit · Ctrl-D   끝내기        Ctrl-C   지금 줄 지우기

연결(DB·Redis·공급자)은 켤 때 한 번 열고 끝낼 때 닫는다 — 명령마다 열지 않는다.
셸 하나에 세션 id 를 붙이고, 사용자 이름과 함께 모든 로그 줄과 명령의 뿌리 span 에
남긴다. 화면에는 WARNING 위의 로그만 찍는다 — LOG_LEVEL 을 직접 주면 그 값
(입구 __main__ 이 정한다).
입력 도구(prompt_toolkit)는 이 파일에서만 쓴다.
"""

import shlex
import sys
import uuid
from collections.abc import Callable
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from agent_builder_infra.observability import bind_context, clear_context, get_logger
from agent_builder_runtime.cli import build_parser, execute
from agent_builder_runtime.cli.render import BOLD, CYAN, DIM, colored, pad, paint, say
from agent_builder_runtime.container import close_all
from agent_builder_runtime.failure_text import (
    no_router_yet,
    shell_bad_quotes,
    shell_unexpected,
)

log = get_logger(__name__)

# 프롬프트 글자를 받아 입력 한 줄을 돌려준다.
# Ctrl-D 는 EOFError, Ctrl-C 는 KeyboardInterrupt 로 알린다 — prompt_toolkit 과 같다.
ReadLine = Callable[[str], str]

# 프롬프트는 「<사용자> › 」. 이 표시로 끝나면 입력 도구가 이름과 표시를 따로 칠한다.
PROMPT_MARK = " › "
# 화면의 세션 id 는 앞 8자만 — 다 보이면 배너가 길다. 전체는 로그 줄·span 에 있다.
SHORT_ID = 8
EXIT_WORDS = frozenset({"/exit", "/quit"})
# 지난 입력. 집 폴더에 둔다 — 친 말이 그대로 남으니 이 PC 사용자만 읽는 곳이어야 한다.
HISTORY_FILE = Path.home() / ".agent-builder" / "shell_history"


def run_shell(user: str | None, read_line: ReadLine | None = None) -> int:
    """끝낼 때까지 한 줄씩 받는다. read_line 은 테스트가 가짜 입력을 넣을 때 쓴다."""
    read = read_line or _prompt_toolkit_reader()
    user = user or _ask_user(read)
    if user is None:
        return 0
    session_id = str(uuid.uuid4())
    bind_context(shell_session_id=session_id, user=user)
    log.info("shell.start")
    _banner(user, session_id)
    prompt = f"{user}{PROMPT_MARK}"
    try:
        while True:
            try:
                line = read(prompt).strip()
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            if not line:
                continue
            if line in EXIT_WORDS:
                break
            if line == "/help":
                print(_help())
                continue
            if line.startswith("/"):
                _command(line[1:], session_id, user)
                continue
            say(no_router_yet(line))
    finally:
        log.info("shell.end")
        clear_context()
        close_all()
    return 0


def _command(text: str, session_id: str, user: str) -> None:
    try:
        argv = shlex.split(text)
    except ValueError as error:
        say(shell_bad_quotes(text, str(error)))
        return
    try:
        execute(argv, **{"shell.session_id": session_id, "user": user})
    except SystemExit:
        # argparse 가 도움말이나 인자 오류를 이미 찍었다. 셸은 계속 받는다.
        return
    except Exception as error:  # noqa: BLE001 — 한 명령의 실패로 셸을 끄지 않는다
        log.error("shell.command.unexpected", command=text, error=type(error).__name__)
        say(shell_unexpected(text, error))


def _ask_user(read: ReadLine) -> str | None:
    """--user 가 없을 때. 끝내면(Ctrl-D) None."""
    while True:
        try:
            name = read("사용자 이름: ").strip()
        except KeyboardInterrupt:
            continue
        except EOFError:
            return None
        if name:
            return name


# 켤 때 뜨는 로고. 영문 기호만 쓴다 — 한국어 글꼴에서 폭이 애매한 글자(█·╭ 등)는
# 두 칸으로 그려져 모양이 깨질 수 있어서.
LOGO = r"""
   ____    _    ____ ___
  / ___|  / \  |  _ \_ _|
 | |  _  / _ \ | | | | |
 | |_| |/ ___ \| |_| | |
  \____/_/   \_\____/___|
"""


def _banner(user: str, session_id: str) -> None:
    on = colored(sys.stdout)
    print(paint(LOGO.strip("\n"), BOLD, CYAN, on=on))
    print()
    print(f"{paint(user, BOLD, CYAN, on=on)}  ·  세션 {session_id[:SHORT_ID]}")
    print(paint("/help 명령 보기 · /exit 끝내기 · 그냥 말은 고르기로", DIM, on=on))


# 셸 자체의 명령. 묶음 명령은 cli 의 파서에서 읽는다.
_SHELL_COMMANDS = (("/help", "이 목록"), ("/exit · /quit", "끝내기 (Ctrl-D)"))
# 이름 칸의 폭 — 가장 긴 묶음 이름(/model-provider)보다 조금 넓게.
_NAME_WIDTH = 19


def _help() -> str:
    """셸의 명령 목록 — 묶음 아래 명령과 한 줄 설명."""
    on = colored(sys.stdout)
    lines = [paint("셸 명령", BOLD, on=on)]
    lines += [f"  {pad(name, _NAME_WIDTH - 2)}{text}" for name, text in _SHELL_COMMANDS]
    parser = build_parser()
    for group, text in _help_lines(parser):
        lines.append("")
        lines.append(paint(pad(f"/{group}", _NAME_WIDTH), BOLD, CYAN, on=on) + text)
        for command, command_text in _help_lines(_subcommands(parser)[group]):
            lines.append(f"  {pad(command, _NAME_WIDTH - 2)}{command_text}")
    lines += [
        "",
        paint("명령 하나의 자세한 인자: /model call --help", DIM, on=on),
        paint("그냥 말 → 진입점(고르기, 아직 없음)", DIM, on=on),
    ]
    return "\n".join(lines)


def _prompt_toolkit_reader(history_file: Path = HISTORY_FILE, **io: object) -> ReadLine:
    """io: prompt_toolkit 의 input·output — 테스트가 콘솔 대신 파이프를 줄 때만 쓴다."""
    history_file.parent.mkdir(parents=True, exist_ok=True)
    session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_file)), completer=_completer(), **io
    )
    style = Style.from_dict({"user": "ansicyan bold", "mark": "ansibrightblack"})

    def read(text: str) -> str:
        return session.prompt(_styled(text), style=style)

    return read


def _styled(text: str) -> FormattedText:
    if text.endswith(PROMPT_MARK):
        name = text[: -len(PROMPT_MARK)]
        return FormattedText([("class:user", name), ("class:mark", PROMPT_MARK)])
    return FormattedText([("", text)])


def _completer() -> "_CommandCompleter":
    """/묶음 명령 을 자동 완성한다 — 명령 목록은 cli 의 파서에서 읽는다."""
    tree: dict[str, list[str]] = {"/help": [], "/exit": [], "/quit": []}
    for group, parser in _subcommands(build_parser()).items():
        tree[f"/{group}"] = list(_subcommands(parser))
    return _CommandCompleter(tree)


class _CommandCompleter(Completer):
    """첫 낱말은 /묶음, 둘째 낱말은 그 묶음의 명령.

    prompt_toolkit 의 NestedCompleter 는 낱말의 경계를 글자·숫자로만 봐서 「/mo」 의
    「/」 를 낱말로 치지 않는다 — 그래서 공백으로만 나누는 것을 따로 둔다.
    """

    def __init__(self, tree: dict[str, list[str]]) -> None:
        self._tree = tree

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        words = text.split(" ")
        if len(words) == 1:
            options, typed = list(self._tree), words[0]
        elif len(words) == 2:
            options, typed = self._tree.get(words[0], []), words[1]
        else:
            return
        for option in options:
            if option.startswith(typed):
                yield Completion(option, start_position=-len(typed))


def _help_lines(parser) -> list[tuple[str, str]]:
    """하위 명령의 (이름, 한 줄 설명) — add_parser(help=...) 에 적은 것."""
    for action in parser._actions:
        if isinstance(getattr(action, "choices", None), dict):
            return [(a.dest, a.help or "") for a in action._choices_actions]
    return []


def _subcommands(parser) -> dict:
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict):
            return choices
    return {}
