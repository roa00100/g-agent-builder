"""모델을 명령줄에서 한 번 부른다. 서비스(ModelGateway)를 부르기만 한다.

python -m agent_builder_runtime model call fast "안녕" --max-tokens 200
python -m agent_builder_runtime model call fast "요약해 줘" \\
    --system "짧게 답한다" --max-tokens 300

응답 텍스트를 찍고, 그 아래에 실제 모델·종료 사유·토큰·비용·걸린 시간을 한 줄로 찍는다.
"""

import argparse
import sys

from pydantic import ValidationError

from agent_builder_core.contracts.model import (
    DisabledModel,
    ModelCallFailed,
    ModelRequest,
    ModelResponse,
    UnknownModel,
    UnknownProvider,
    UnsupportedInput,
)
from agent_builder_core.model import UnresolvedSource
from agent_builder_runtime.container import close_all, get_model_gateway

# 종료 코드. 0 성공, 1 없거나 꺼진 모델·공급자, 2 입력값이 맞지 않음, 3 호출 실패.
EXIT_UNKNOWN = 1
EXIT_INVALID = 2
EXIT_FAILED = 3


def register(groups: argparse._SubParsersAction) -> None:
    parser = groups.add_parser("model", help="모델 부르기")
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


def run(args: argparse.Namespace) -> int:
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
    finally:
        close_all()
    print(response.text())
    print(_summary(response), file=sys.stderr)
    return 0


def _summary(response: ModelResponse) -> str:
    usage = response.usage
    cost = "모름" if usage.cost is None else f"{usage.cost} 크레딧"
    return (
        f"[{response.provider_model} · {response.finish_reason}"
        f"({response.finish_detail}) · 입력 {usage.input_tokens} / "
        f"출력 {usage.output_tokens} 토큰 · 비용 {cost} · "
        f"{response.latency_ms}ms · request_id {response.request_id}]"
    )
