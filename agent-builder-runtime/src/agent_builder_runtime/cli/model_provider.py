"""공급자 프로필을 명령줄에서 보고 고친다. API 키는 어디에도 찍지 않는다.

python -m agent_builder_runtime model-provider list
python -m agent_builder_runtime model-provider show openrouter
python -m agent_builder_runtime model-provider set openrouter \\
    --base-url https://openrouter.ai/api/v1 --timeout 60
python -m agent_builder_runtime model-provider set-key openrouter
    (입력이 화면에 안 보인다)
python -m agent_builder_runtime model-provider set-key openrouter --stdin
    (파이프로 넘길 때)
python -m agent_builder_runtime model-provider disable openrouter
python -m agent_builder_runtime model-provider delete openrouter
"""

import argparse
import getpass
import sys

from pydantic import ValidationError

from agent_builder_core.contracts.model import UnknownProvider
from agent_builder_infra.services import CipherError
from agent_builder_runtime.cli.render import say, table
from agent_builder_runtime.container import (
    MissingMasterKey,
    get_provider_profiles,
)
from agent_builder_runtime.failure_text import explain
from agent_builder_runtime.repositories import ProviderProfile

# 종료 코드. 0 성공, 1 없는 공급자, 2 입력값이 맞지 않음.
EXIT_UNKNOWN = 1
EXIT_INVALID = 2


def register(groups: argparse._SubParsersAction) -> None:
    parser = groups.add_parser(
        "model-provider", help="공급자 프로필 (주소·API 키·대기 시간)"
    )
    parser.set_defaults(run=run)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="전부 보기 (키는 있음·없음만)")
    for name, text in [
        ("show", "한 줄 보기 (키는 있음·없음만)"),
        ("enable", "켜기"),
        ("disable", "끄기: 이 공급자로 보내지 않는다"),
        ("delete", "지우기"),
    ]:
        sub.add_parser(name, help=text).add_argument("name")
    set_parser = sub.add_parser("set", help="주소·대기 시간 넣거나 바꾸기 (켠 상태로)")
    set_parser.add_argument("name", help="공급자 이름 (예: openrouter)")
    set_parser.add_argument("--base-url", required=True, help="공급자 API 주소")
    # 기본값을 두지 않는다 — 기다릴 시간은 넣는 사람이 정한다(E18).
    set_parser.add_argument(
        "--timeout", type=float, required=True, help="호출 한 번을 기다릴 기본 시간(초)"
    )
    key_parser = sub.add_parser("set-key", help="API 키 넣기 (암호화해 저장한다)")
    key_parser.add_argument("name")
    key_parser.add_argument(
        "--stdin",
        action="store_true",
        help="키를 표준 입력에서 읽는다 (화면 입력 대신)",
    )


def run(args: argparse.Namespace) -> int:
    profiles = get_provider_profiles()
    try:
        if args.command == "list":
            table(HEADERS, [_cells(profile) for profile in profiles.list()])
        elif args.command == "show":
            profile = profiles.get(args.name)
            if profile is None:
                raise UnknownProvider(args.name, "no_profile")
            print(_detail(profile))
        elif args.command == "set":
            profiles.save(
                args.name, base_url=args.base_url, timeout_seconds=args.timeout
            )
            table(HEADERS, [_cells(profiles.get(args.name))])
        elif args.command == "set-key":
            api_key = (
                sys.stdin.readline().strip()
                if args.stdin
                else getpass.getpass("API 키: ")
            )
            profiles.set_api_key(args.name, api_key)
            print(f"키를 넣었다: {args.name}")
        elif args.command in ("enable", "disable"):
            profiles.set_enabled(args.name, args.command == "enable")
            table(HEADERS, [_cells(profiles.get(args.name))])
        elif args.command == "delete":
            if not profiles.delete(args.name):
                raise UnknownProvider(args.name, "no_profile")
            print(f"지움: {args.name}")
    except (UnknownProvider, MissingMasterKey, CipherError) as error:
        say(explain(error, "manage"))
        return EXIT_UNKNOWN
    except (ValidationError, ValueError) as error:
        say(explain(error, "manage"))
        return EXIT_INVALID
    return 0


# 표의 머리줄. 화면에 찍을 때만 보인다 — 파이프로 넘기면 탭으로 나눈 줄만 나간다.
HEADERS = ("이름", "주소", "대기", "키", "상태")


def _cells(profile: ProviderProfile) -> tuple[str, ...]:
    state = "켜짐" if profile.enabled else "꺼짐"
    key = "키 있음" if profile.has_api_key else "키 없음"
    return (
        profile.name,
        profile.base_url,
        f"{profile.timeout_seconds:g}초",
        key,
        state,
    )


def _detail(profile: ProviderProfile) -> str:
    # 암호문도 찍지 않는다 — 있음·없음만.
    return "\n".join(
        [
            f"name: {profile.name}",
            f"base_url: {profile.base_url}",
            f"timeout_seconds: {profile.timeout_seconds:g}",
            f"api_key: {'있음' if profile.has_api_key else '없음'}",
            f"enabled: {profile.enabled}",
            f"updated_at: {profile.updated_at.isoformat()}",
        ]
    )
