"""명령줄 진입점.

python -m agent_builder_runtime --help
python -m agent_builder_runtime model-alias list
"""

import argparse
import sys
from collections.abc import Sequence

from agent_builder_runtime.cli import model_alias


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m agent_builder_runtime",
        description="에이전트 빌더 명령줄.",
    )
    groups = parser.add_subparsers(dest="group", required=True)
    model_alias.register(groups)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
