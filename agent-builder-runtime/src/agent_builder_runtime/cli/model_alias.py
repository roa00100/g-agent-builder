"""모델 논리 이름의 대응표를 명령줄에서 보고 고친다.

python -m agent_builder_runtime model-alias list
python -m agent_builder_runtime model-alias show fast
python -m agent_builder_runtime model-alias set fast --provider openrouter \\
    --model <공급자 쪽 이름> --inputs text,image
python -m agent_builder_runtime model-alias disable fast
python -m agent_builder_runtime model-alias enable fast
python -m agent_builder_runtime model-alias delete fast

여기는 서비스를 부르기만 한다. 고칠 때 캐시를 지우는 일 등은 서비스가 한다.
"""

import argparse
import sys

from pydantic import ValidationError

from agent_builder_infra.model_alias import ModelAlias, UnknownModelAlias
from agent_builder_runtime.container import close_all, get_model_alias_service

# 종료 코드. 0 성공, 1 없는 이름, 2 입력값이 모양에 맞지 않음(argparse 의 관례와 같다).
EXIT_UNKNOWN = 1
EXIT_INVALID = 2


def register(groups: argparse._SubParsersAction) -> None:
    parser = groups.add_parser("model-alias", help="모델 논리 이름의 대응표")
    parser.set_defaults(run=run)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="전부 보기")
    for name, text in [
        ("show", "한 줄 보기"),
        ("enable", "켜기"),
        ("disable", "끄기: 이 이름으로 오는 요청을 거부한다"),
        ("delete", "지우기"),
    ]:
        sub.add_parser(name, help=text).add_argument("name")
    set_parser = sub.add_parser("set", help="넣거나 바꾸기 (켠 상태로)")
    set_parser.add_argument("name", help="논리 이름 (예: fast)")
    set_parser.add_argument("--provider", required=True, help="공급자 (예: openrouter)")
    set_parser.add_argument("--model", required=True, help="공급자 쪽 실제 모델 이름")
    set_parser.add_argument(
        "--inputs",
        # 기본은 텍스트만. 이미지·파일을 받는 모델이면 적어야 한다 — 받지 못하는 조각을
        # 받는다고 잘못 적는 것보다 빠뜨리는 쪽이 오류로 빨리 드러난다.
        default="text",
        help="받는 조각, 쉼표로 (text,image,file). 기본 text",
    )


def run(args: argparse.Namespace) -> int:
    service = get_model_alias_service()
    try:
        if args.command == "list":
            for alias in service.list():
                print(_line(alias))
        elif args.command == "show":
            alias = service.get(args.name)
            if alias is None:
                raise UnknownModelAlias(f"대응표에 없는 모델 이름: {args.name}")
            print(alias.model_dump_json(indent=2))
        elif args.command == "set":
            alias = ModelAlias(
                name=args.name,
                provider=args.provider,
                provider_model=args.model,
                input_kinds=tuple(k.strip() for k in args.inputs.split(",") if k),
            )
            service.upsert(alias)
            print(_line(alias))
        elif args.command in ("enable", "disable"):
            service.set_enabled(args.name, args.command == "enable")
            print(_line(service.get(args.name)))
        elif args.command == "delete":
            if not service.delete(args.name):
                raise UnknownModelAlias(f"대응표에 없는 모델 이름: {args.name}")
            print(f"지움: {args.name}")
    except UnknownModelAlias as error:
        print(error, file=sys.stderr)
        return EXIT_UNKNOWN
    except ValidationError as error:
        print(error, file=sys.stderr)
        return EXIT_INVALID
    finally:
        close_all()
    return 0


def _line(alias: ModelAlias) -> str:
    state = "켜짐" if alias.enabled else "꺼짐"
    kinds = ",".join(alias.input_kinds)
    return f"{alias.name}\t{alias.provider}\t{alias.provider_model}\t{kinds}\t{state}"
