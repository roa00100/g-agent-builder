"""실행 입구. 프로필로 모드를 고르기만 한다.

python -m agent_builder_runtime model-catalog list              (기본 cli 모드)
python -m agent_builder_runtime --profile cli model-catalog list
python -m agent_builder_runtime --profile rest                   (REST 서버)

프로필은 --profile 인자, 없으면 환경변수 RUNTIME_PROFILE, 없으면 cli 다.
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
    profile, rest_of_args = _pick_profile(sys.argv[1:] if argv is None else argv)
    if profile == "rest":
        # 웹 프레임워크는 rest 모드에서만 불러온다.
        from agent_builder_runtime import rest

        if rest_of_args:
            print(f"rest 모드는 인자를 받지 않는다: {rest_of_args}", file=sys.stderr)
            return 2
        rest.run()
        return 0

    from agent_builder_runtime import cli

    return cli.run(rest_of_args)


def _pick_profile(argv: Sequence[str]) -> tuple[Profile, list[str]]:
    """--profile 만 먼저 읽고, 나머지 인자는 고른 모드에 넘긴다."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--profile", choices=get_args(Profile))
    known, rest_of_args = parser.parse_known_args(list(argv))
    profile = known.profile or get_runtime_settings().runtime_profile
    return profile, rest_of_args


if __name__ == "__main__":
    sys.exit(main())
