import ast
import importlib
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "name",
    [
        "agent_builder_runtime",
        "agent_builder_runtime.__main__",
        "agent_builder_runtime.cli",
        "agent_builder_runtime.container",
        "agent_builder_runtime.repositories",
        "agent_builder_runtime.repositories.model_catalog",
        "agent_builder_runtime.cli.model_alias",
    ],
)
def test_package_imports(name):
    importlib.import_module(name)


def test_runtime_does_not_use_db_technology_directly():
    # DB 기술은 infra 가 맡는다. runtime 은 infra 가 주는 것만 쓴다.
    import agent_builder_runtime

    src = Path(agent_builder_runtime.__file__).parent
    found = []
    for path in src.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] in {"sqlalchemy", "psycopg", "redis", "boto3"}:
                    found.append(f"{path.name}: {name}")

    assert found == []
