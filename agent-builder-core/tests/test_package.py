import importlib
import sys

import pytest

PACKAGES = [
    "agent_builder_core",
    "agent_builder_core.contracts",
    "agent_builder_core.contracts.envelope",
    "agent_builder_core.contracts.model",
    "agent_builder_core.contracts.model.request",
    "agent_builder_core.contracts.model.response",
    "agent_builder_core.contracts.model.provider",
    "agent_builder_core.model",
    "agent_builder_core.model.service",
    "agent_builder_core.workflow",
    "agent_builder_core.run",
    "agent_builder_core.assist",
]

# core 가 알면 안 되는 기술 패키지.
FORBIDDEN = [
    "sqlalchemy",
    "psycopg",
    "redis",
    "openai",
    "alembic",
    "boto3",
    # 관측도 기술이다 — core 에는 추적·로그 코드를 넣지 않는다.
    "opentelemetry",
    "structlog",
    "agent_builder_infra",
    "agent_builder_runtime",
]


@pytest.mark.parametrize("name", PACKAGES)
def test_package_imports(name):
    importlib.import_module(name)


def test_core_does_not_import_technology():
    for name in PACKAGES:
        importlib.import_module(name)

    loaded = [name for name in FORBIDDEN if name in sys.modules]

    assert loaded == []
