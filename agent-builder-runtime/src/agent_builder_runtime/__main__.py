"""실행 입구. 프로필로 모드를 고르기만 한다.

python -m agent_builder_runtime                         (cli — 셸이 뜬다)
python -m agent_builder_runtime --user 김재형           (셸, 사용자 이름을 준다)
python -m agent_builder_runtime model-catalog list     (cli — 한 번 하고 끝)
python -m agent_builder_runtime --profile cli model-catalog list
python -m agent_builder_runtime --profile rest                   (REST 서버)

프로필은 --profile 인자, 없으면 환경변수 RUNTIME_PROFILE, 없으면 cli 다.
cli 모드에서 명령을 주지 않으면 셸, 주면 그 명령 하나만 한다.
--user 는 사람의 이름이다 — 셸은 없으면 켤 때 묻는다. 한 번 하고 끝나는 명령은 아직
사람의 손(확인·답)이 없어 쓰지 않는다.
"""

import argparse
import sys
from collections.abc import Sequence
from typing import get_args

from agent_builder_runtime.observability import setup_observability
from agent_builder_runtime.settings import Profile, get_runtime_settings


def main(argv: Sequence[str] | None = None) -> int:
    # 연결을 만들기 전에 켜야 DB·Redis·HTTP 호출이 span 으로 잡힌다.
    setup_observability()
    profile, user, rest_of_args = _pick_profile(sys.argv[1:] if argv is None else argv)
    if profile == "rest":
        # 웹 프레임워크는 rest 모드에서만 불러온다.
        from agent_builder_runtime import rest

        if rest_of_args:
            print(f"rest 모드는 인자를 받지 않는다: {rest_of_args}", file=sys.stderr)
            return 2
        rest.run()
        return 0

    from agent_builder_runtime import cli

    if not rest_of_args:
        # 입력 도구(prompt_toolkit)는 셸을 켤 때만 불러온다.
        from agent_builder_runtime.cli.shell import run_shell
        from agent_builder_runtime.observability import quiet_logs_for_shell

        quiet_logs_for_shell()
        return run_shell(user)
    return cli.run(rest_of_args)


def _pick_profile(argv: Sequence[str]) -> tuple[Profile, str | None, list[str]]:
    """--profile·--user 만 먼저 읽고, 나머지 인자는 고른 모드에 넘긴다."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--profile", choices=get_args(Profile))
    parser.add_argument("--user")
    known, rest_of_args = parser.parse_known_args(list(argv))
    profile = known.profile or get_runtime_settings().runtime_profile
    return profile, known.user, rest_of_args


if __name__ == "__main__":
    sys.exit(main())
