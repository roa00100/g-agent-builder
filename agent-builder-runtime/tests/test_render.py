"""출력의 모양 — 화면이면 표·색, 파이프면 지금까지의 모양 그대로."""

import io
import re

import pytest

from agent_builder_runtime.cli import render
from agent_builder_runtime.failure_text import CLI, Explanation

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture(autouse=True)
def _colors_on(monkeypatch):
    # 이 테스트를 도는 환경에 NO_COLOR 가 있을 수 있다.
    monkeypatch.delenv("NO_COLOR", raising=False)


class Screen(io.StringIO):
    """isatty 가 참인 흐름 — 터미널 대신."""

    def isatty(self) -> bool:
        return True


def plain(text: str) -> str:
    return _ANSI.sub("", text)


def test_piped_table_is_tab_lines_without_header():
    out = io.StringIO()

    render.table(("이름", "상태"), [("fast", "켜짐"), ("smart", "꺼짐")], out)

    assert out.getvalue() == "fast\t켜짐\nsmart\t꺼짐\n"


def test_screen_table_aligns_wide_letters():
    out = Screen()

    render.table(("이름", "공급자"), [("빠른모델", "openrouter"), ("x", "y")], out)

    header, rule, first, second = plain(out.getvalue()).splitlines()
    # 「빠른모델」 은 여덟 칸 — 둘째 칸이 모든 줄에서 같은 자리에서 시작한다.
    assert render.width(header[: header.index("공급자")]) == 8 + 2
    assert render.width(first[: first.index("openrouter")]) == 8 + 2
    assert render.width(second[: second.index("y")]) == 8 + 2
    assert rule.startswith("─" * 8 + "  ")
    assert not first.endswith(" ")


def test_screen_table_without_rows_says_none():
    out = Screen()

    render.table(("이름",), [], out)

    assert plain(out.getvalue()).splitlines()[-1] == "(없음)"


def test_piped_failure_is_the_same_text():
    explanation = Explanation(
        "못 했습니다.", ("보내지 않았습니다.",), ("다시 합니다.",)
    )
    out = io.StringIO()

    render.say(explanation, out)

    assert out.getvalue() == explanation.text() + "\n"


def test_screen_failure_colors_message_and_commands():
    explanation = Explanation(
        "못 했습니다.",
        ("보내지 않았습니다.",),
        (f"켜기: {CLI} model-catalog enable fast, 또는 그대로 둡니다",),
    )
    out = Screen()

    render.say(explanation, out)

    text = out.getvalue()
    assert "\x1b[1;31m✗ 못 했습니다.\x1b[0m" in text
    assert f"\x1b[36m{CLI} model-catalog enable fast\x1b[0m, 또는" in text
    assert plain(text).splitlines() == [
        "✗ 못 했습니다.",
        "    · 보내지 않았습니다.",
        "  할 일",
        f"    → 켜기: {CLI} model-catalog enable fast, 또는 그대로 둡니다",
    ]


def test_no_color_keeps_layout_without_escapes(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    out = Screen()

    render.table(("이름",), [("fast",)], out)
    render.say(Explanation("못 했습니다."), out)

    assert "[" not in out.getvalue()
    assert out.getvalue().splitlines() == ["이름", "────", "fast", "✗ 못 했습니다."]


def test_width_counts_korean_as_two():
    assert render.width("ab한글") == 6
