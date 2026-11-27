import importlib

import pytest


@pytest.mark.parametrize(
    "name",
    [
        "agent_builder_infra",
        "agent_builder_infra.providers",
        "agent_builder_infra.services",
        "agent_builder_infra.crud",
        "agent_builder_infra.orm",
        "agent_builder_infra.clients",
        "agent_builder_infra.clients.openrouter",
        "agent_builder_infra.services.cipher",
        "agent_builder_infra.tables",
        "agent_builder_infra.tables.model_provider",
        "agent_builder_infra.tables.model_alias",
        "agent_builder_infra.providers.object_storage",
        "agent_builder_infra.services.object_storage",
        "agent_builder_infra.observability",
        "agent_builder_infra.observability.sql",
    ],
)
def test_package_imports(name):
    importlib.import_module(name)


def test_infra_does_not_import_runtime():
    # infra 는 runtime 이 쓰는 쪽이다. 반대 방향 import 는 없어야 한다.
    # core 는 안쪽이라 infra 가 import 해도 된다.
    import sys

    import agent_builder_infra.providers  # noqa: F401
    import agent_builder_infra.services  # noqa: F401
    import agent_builder_infra.tables.model_alias  # noqa: F401

    assert "agent_builder_runtime" not in sys.modules
