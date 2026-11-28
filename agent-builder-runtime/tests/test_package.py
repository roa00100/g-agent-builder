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
        "agent_builder_runtime.model_adapters",
        "agent_builder_runtime.model_adapters.connections",
        "agent_builder_runtime.model_adapters.openrouter",
        "agent_builder_runtime.model_adapters.openrouter.errors",
        "agent_builder_runtime.model_adapters.openrouter.adapter",
        "agent_builder_runtime.model_adapters.openrouter.request",
        "agent_builder_runtime.model_adapters.openrouter.response",
        "agent_builder_runtime.repositories",
        "agent_builder_runtime.repositories.model_catalog",
        "agent_builder_runtime.repositories.provider_profile",
        "agent_builder_runtime.cli.model",
        "agent_builder_runtime.cli.model_catalog",
        "agent_builder_runtime.cli.model_provider",
        "agent_builder_runtime.cli.shell",
        "agent_builder_runtime.failure_text",
        "agent_builder_runtime.rest",
        "agent_builder_runtime.rest.model",
        "agent_builder_runtime.rest.model_catalog",
        "agent_builder_runtime.rest.model_provider",
        "agent_builder_runtime.settings",
        "agent_builder_runtime.observability",
    ],
)
def test_package_imports(name):
    importlib.import_module(name)


def test_runtime_does_not_use_db_technology_directly():
    # DB·모델 SDK 같은 기술은 infra 가 맡는다. runtime 은 infra 가 주는 것만 쓴다.
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
                if name.split(".")[0] in {
                    "sqlalchemy",
                    "psycopg",
                    "redis",
                    "boto3",
                    "openai",
                    "cryptography",
                }:
                    found.append(f"{path.name}: {name}")

    assert found == []


def test_web_framework_only_in_rest():
    # 웹 프레임워크는 REST 진입 계층(rest/)에만 둔다.
    import agent_builder_runtime

    src = Path(agent_builder_runtime.__file__).parent
    found = []
    for path in src.rglob("*.py"):
        if "rest" in path.relative_to(src).parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] in {"fastapi", "starlette", "uvicorn"}:
                    found.append(f"{path.name}: {name}")

    assert found == []


def test_observability_technology_only_through_infra():
    # 로그·추적은 infra 의 observability 를 거친다. 예외는 rest/ 의 FastAPI 계측 하나 —
    # 웹 프레임워크를 아는 계측이라 웹 프레임워크와 같은 자리에 둔다.
    import agent_builder_runtime

    src = Path(agent_builder_runtime.__file__).parent
    found = []
    for path in src.rglob("*.py"):
        in_rest = "rest" in path.relative_to(src).parts
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] == "structlog":
                    found.append(f"{path.name}: {name}")
                elif name.split(".")[0] == "opentelemetry" and not (
                    in_rest and name.startswith("opentelemetry.instrumentation.fastapi")
                ):
                    found.append(f"{path.name}: {name}")

    assert found == []


def test_prompt_toolkit_only_in_shell():
    # 셸의 입력 도구는 cli/shell.py 에서만 쓴다.
    import agent_builder_runtime

    src = Path(agent_builder_runtime.__file__).parent
    found = []
    for path in src.rglob("*.py"):
        if path.relative_to(src).parts == ("cli", "shell.py"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name.split(".")[0] == "prompt_toolkit":
                    found.append(f"{path.name}: {name}")

    assert found == []
