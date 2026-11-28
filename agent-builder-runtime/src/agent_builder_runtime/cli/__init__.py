"""cli 모드 — 명령 하나를 실행하고 끝나거나(run), 켜 둔 채로 계속 받는다(셸, shell.py).

묶음마다 모듈 하나 — register() 로 묶음을 달고, run() 으로 실행한다.
묶음은 서비스(계약)를 부르기만 하고, 연결을 닫지 않는다 — 닫는 것은 한 번 하고
끝나는 run() 과 셸이 끝날 때다. 셸에서는 명령마다 연결을 새로 열지 않는다.
"""

import argparse
from collections.abc import Sequence
from typing import Any

from agent_builder_infra.observability import span
from agent_builder_runtime.cli import model, model_catalog, model_provider
from agent_builder_runtime.container import close_all

# 묶음을 더하면 여기에 모듈을 넣는다.
_GROUPS = (model, model_catalog, model_provider)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agent_builder_runtime [--profile cli]",
        description="에이전트 빌더 명령줄.",
    )
    groups = parser.add_subparsers(dest="group", required=True)
    for group in _GROUPS:
        group.register(groups)
    return parser


def run(argv: Sequence[str]) -> int:
    """명령 하나를 실행하고 연결을 닫는다."""
    try:
        return execute(argv)
    finally:
        close_all()


def execute(argv: Sequence[str], **attributes: Any) -> int:
    """명령 하나를 실행한다. 연결은 닫지 않는다 — 셸이 이어서 쓴다.

    인자가 틀리면 argparse 가 까닭을 찍고 SystemExit 을 올린다.
    attributes: 뿌리 span 에 더할 값 (셸의 세션 id·사용자 등).
    """
    args = build_parser().parse_args(list(argv))
    # 명령 하나가 추적 하나의 뿌리 span 이 된다.
    command = getattr(args, "command", None)
    with span(f"cli {args.group} {command}", **{"cli.group": args.group, **attributes}):
        return args.run(args)
