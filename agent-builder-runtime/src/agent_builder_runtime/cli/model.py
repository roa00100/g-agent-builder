"""모델을 명령줄에서 부르고, 남은 호출 기록을 본다. 서비스·계약을 부르기만 한다.

python -m agent_builder_runtime model call fast "안녕" --max-tokens 200
python -m agent_builder_runtime model call fast "요약해 줘" \\
    --system "짧게 답한다" --max-tokens 300
python -m agent_builder_runtime model calls --limit 20
python -m agent_builder_runtime model call-show <request_id>

call 은 응답 텍스트만 stdout 에 찍는다. 실제 모델·종료 사유·토큰·비용·걸린 시간은
INFO 로그 model.call.done 한 줄(stderr)에 있다 — 같은 것을 여기서 또 찍지 않는다.
실패는 여기서도 찍는다 — 종료 코드의 까닭은 로그 단계와 상관없이 보여야 해서.
"""

import argparse
import sys

from pydantic import ValidationError

from agent_builder_core.contracts.model import (
    CallRecord,
    DisabledModel,
    ModelCallFailed,
    ModelRequest,
    UnknownModel,
    UnknownProvider,
    UnsupportedInput,
)
from agent_builder_core.model import UnresolvedSource
from agent_builder_runtime.container import close_all, get_call_log, get_model_gateway

# 종료 코드. 0 성공, 1 없거나 꺼진 모델·공급자(또는 없는 기록), 2 입력값이 맞지 않음,
# 3 호출 실패.
EXIT_UNKNOWN = 1
EXIT_INVALID = 2
EXIT_FAILED = 3

# 기록 목록의 기본 개수. 한 화면에 들어오는 정도다.
DEFAULT_LIMIT = 20


def register(groups: argparse._SubParsersAction) -> None:
    parser = groups.add_parser("model", help="모델 부르기와 호출 기록")
    parser.set_defaults(run=run)
    sub = parser.add_subparsers(dest="command", required=True)
    call = sub.add_parser("call", help="모델에 메시지 하나를 보내고 답을 받는다")
    call.add_argument("model", help="논리 이름 (예: fast)")
    call.add_argument("message", help="보낼 말")
    call.add_argument("--system", default=None, help="시스템 지침")
    # 기본값을 두지 않는다 — 응답 길이 상한은 부르는 사람이 정한다(E18).
    call.add_argument(
        "--max-tokens", type=int, required=True, help="응답 길이 상한 (토큰)"
    )
    calls = sub.add_parser("calls", help="최근 호출 기록 (최근 것부터)")
    calls.add_argument(
        "--limit", type=int, default=DEFAULT_LIMIT, help=f"몇 줄 (기본 {DEFAULT_LIMIT})"
    )
    show = sub.add_parser("call-show", help="호출 기록 한 줄 자세히")
    show.add_argument("request_id")


def run(args: argparse.Namespace) -> int:
    try:
        if args.command == "call":
            return _call(args)
        if args.command == "calls":
            if args.limit < 1:
                print("--limit 은 1 이상이다", file=sys.stderr)
                return EXIT_INVALID
            for record in get_call_log().list(args.limit):
                print(_line(record))
            return 0
        record = get_call_log().get(args.request_id)
        if record is None:
            print(f"호출 기록이 없다: {args.request_id}", file=sys.stderr)
            return EXIT_UNKNOWN
        print(record.model_dump_json(indent=2))
        return 0
    finally:
        close_all()


def _call(args: argparse.Namespace) -> int:
    try:
        request = ModelRequest(
            model=args.model,
            system=args.system,
            messages=[{"role": "user", "content": args.message}],
            params={"max_output_tokens": args.max_tokens},
        )
        response = get_model_gateway().complete(request)
    except (UnknownModel, DisabledModel, UnknownProvider) as error:
        print(error, file=sys.stderr)
        return EXIT_UNKNOWN
    except (ValidationError, UnsupportedInput, UnresolvedSource) as error:
        print(error, file=sys.stderr)
        return EXIT_INVALID
    except ModelCallFailed as error:
        again = "다시 보내 볼 만함" if error.retryable else "다시 보내도 같음"
        print(f"호출 실패 [{error.kind}, {again}] {error.detail}", file=sys.stderr)
        print(f"request_id: {error.request_id}", file=sys.stderr)
        return EXIT_FAILED
    print(response.text())
    return 0


def _line(record: CallRecord) -> str:
    """시각·request_id·모델·결과·토큰·비용·걸린 시간을 탭으로 나눈 한 줄."""
    when = record.started_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    if record.status == "ok":
        result = record.finish_reason
        tokens = f"{record.input_tokens}/{record.output_tokens}"
    else:
        result = f"실패:{record.failure_kind}"
        tokens = "-"
    cost = "-" if record.cost is None else str(record.cost)
    return (
        f"{when}\t{record.request_id}\t{record.model}\t{record.provider_model}"
        f"\t{result}\t{tokens}\t{cost}\t{record.latency_ms}ms"
    )
