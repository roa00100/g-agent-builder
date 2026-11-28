"""명령줄 출력의 모양 — 표, 실패 문장의 색, 글자 꾸밈.

화면(터미널)에 찍을 때만 꾸민다(NO_COLOR 가 있으면 자리만 맞추고 색은 뺀다).
파일·파이프로 넘길 때는 지금까지의 모양 그대로다 — 표는 탭으로 나눈 줄(머리줄 없음),
실패 문장은 Explanation.text(). 다른 도구가 읽는 출력을 꾸밈 때문에 바꾸지 않으려는
것이다.

문장은 failure_text 가 만든다. 여기서는 색과 자리만 정한다.
색은 ANSI 이스케이프로 직접 쓴다 — 입력 도구(prompt_toolkit)는 shell.py 에서만 쓴다.
"""

import os
import re
import sys
import unicodedata
from collections.abc import Iterable, Sequence
from typing import TextIO

from agent_builder_runtime.failure_text import CLI, Explanation

# ANSI SGR 번호. 색은 터미널 테마가 정하도록 16색 번호만 쓴다(RGB 를 고르지 않는다).
BOLD = "1"
DIM = "2"
RED = "31"
YELLOW = "33"
CYAN = "36"

# 할 일 문장 안에서 명령으로 칠할 자리 — CLI 로 시작해 쉼표나 줄 끝까지.
# failure_text 가 명령을 「설명: python -m … 명령」 꼴로 쓰고, 여럿이면 쉼표로 잇는다.
_COMMAND = re.compile(re.escape(CLI) + r"[^,]*")

# 칸 사이 공백. 탭 대신 — 탭은 8칸 자리로 끊겨 한글이 섞이면 줄이 어긋난다.
_GAP = "  "

_vt_ready = False


def colored(stream: TextIO) -> bool:
    """이 흐름에 색을 써도 되는가 — 화면(터미널)이고 NO_COLOR 가 없을 때.

    NO_COLOR 가 있으면 색만 끈다(표 정렬은 그대로). 셸의 프롬프트를 그리는
    prompt_toolkit 도 이 관례를 따르므로, 두 쪽이 같이 꺼지고 켜진다.
    """
    if not stream.isatty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    _enable_vt()
    return True


def paint(text: str, *codes: str, on: bool = True) -> str:
    if not on or not codes:
        return text
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


def width(text: str) -> int:
    """화면에서 차지하는 칸 수. 한글·한자 같은 넓은 글자는 두 칸이다.

    애매한 폭(East Asian Ambiguous — ·, ─ 등)은 한 칸으로 본다. 한국어 콘솔 글꼴에
    따라 두 칸으로 그리는 곳도 있지만, 표의 칸 값에는 거의 나오지 않는다.
    """
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def pad(text: str, size: int) -> str:
    return text + " " * max(size - width(text), 0)


def table(
    headers: Sequence[str],
    rows: Iterable[Sequence[object]],
    stream: TextIO | None = None,
) -> None:
    """화면이면 머리줄 있는 표, 아니면 탭으로 나눈 줄(머리줄 없음)."""
    out = stream or sys.stdout
    cells = [[str(cell) for cell in row] for row in rows]
    if not out.isatty():
        for row in cells:
            print("\t".join(row), file=out)
        return
    on = colored(out)
    widths = [
        max(width(cell) for cell in column)
        for column in zip(headers, *cells, strict=True)
    ]
    print(paint(_join(headers, widths), BOLD, on=on), file=out)
    print(paint(_GAP.join("─" * size for size in widths), DIM, on=on), file=out)
    for row in cells:
        print(_join(row, widths), file=out)
    if not cells:
        print(paint("(없음)", DIM, on=on), file=out)


def _join(row: Sequence[str], widths: Sequence[int]) -> str:
    # 마지막 칸은 채우지 않는다 — 줄 끝에 공백이 남지 않게.
    return _GAP.join(
        [pad(cell, size) for cell, size in zip(row[:-1], widths[:-1], strict=True)]
        + [row[-1]]
    )


def say(explanation: Explanation, stream: TextIO | None = None) -> None:
    """실패 문장을 찍는다. 화면이면 색과 들여쓰기, 아니면 Explanation.text() 그대로."""
    out = stream or sys.stderr
    if not out.isatty():
        print(explanation.text(), file=out)
        return
    on = colored(out)
    lines = [paint(f"✗ {explanation.message}", BOLD, RED, on=on)]
    # 사실은 흐리게 하지 않는다 — 보냈는가·비용·남은 것 같은 중요한 말이라.
    lines += [f"    {paint('·', DIM, on=on)} {fact}" for fact in explanation.facts]
    if explanation.next:
        lines.append("  " + paint("할 일", BOLD, YELLOW, on=on))
        lines += [
            f"    {paint('→', YELLOW, on=on)} "
            + _COMMAND.sub(lambda m: paint(m.group(0), CYAN, on=on), step)
            for step in explanation.next
        ]
    print("\n".join(lines), file=out)


def _enable_vt() -> None:
    """Windows 콘솔이 ANSI 이스케이프를 색으로 그리게 한다(한 번만).

    옛 콘솔(conhost)은 이 모드를 켜지 않으면 이스케이프를 글자 그대로 찍는다.
    Windows Terminal·IntelliJ 터미널은 이미 켜져 있어 아무 일도 하지 않는다.
    """
    global _vt_ready
    if _vt_ready or sys.platform != "win32":
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    # -11 STD_OUTPUT_HANDLE, -12 STD_ERROR_HANDLE
    # 0x0004 ENABLE_VIRTUAL_TERMINAL_PROCESSING
    for handle_id in (-11, -12):
        handle = kernel32.GetStdHandle(handle_id)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    _vt_ready = True
