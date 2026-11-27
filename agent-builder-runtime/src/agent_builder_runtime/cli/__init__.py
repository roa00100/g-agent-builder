"""cli 모드 — 명령 하나를 실행하고 끝난다.

묶음마다 모듈 하나 — register() 로 묶음을 달고, run() 으로 실행한다.
묶음은 서비스(계약)를 부르기만 한다.
"""

import argparse
from collections.abc import Sequence

from agent_builder_infra.observability import span
from agent_builder_runtime.cli import model, model_catalog, model_provider

# 묶음을 더하면 여기에 모듈을 넣는다.
_GROUPS = (model, model_catalog, model_provider)


def run(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m agent_builder_runtime [--profile cli]",
        description="에이전트 빌더 명령줄.",
    )
    groups = parser.add_subparsers(dest="group", required=True)
    for group in _GROUPS:
        group.register(groups)
    args = parser.parse_args(list(argv))
    # 명령 하나가 추적 하나의 뿌리 span 이 된다.
    command = getattr(args, "command", None)
    with span(f"cli {args.group} {command}", **{"cli.group": args.group}):
        return args.run(args)
    return None
