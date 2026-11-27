"""명령줄 도움말이 Windows 기본 인코딩(cp949)으로 찍히는지.

출력을 파일·파이프로 넘기면 파이썬은 cp949 로 쓴다. 도움말에 cp949 에 없는 글자
(예: 긴 줄표 —)가 있으면 --help 가 UnicodeEncodeError 로 죽는다.
"""

import argparse

from agent_builder_runtime.cli import build_parser


def all_parsers(parser: argparse.ArgumentParser):
    yield parser
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                yield from all_parsers(child)


def test_every_help_screen_encodes_in_cp949():
    broken = []
    for parser in all_parsers(build_parser()):
        try:
            parser.format_help().encode("cp949")
        except UnicodeEncodeError as error:
            broken.append(f"{parser.prog}: {error.object[error.start]!r}")

    assert broken == []
