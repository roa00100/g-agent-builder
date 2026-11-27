import importlib

import pytest


@pytest.mark.parametrize(
    "name",
    [
        "agent_builder_infra",
        "agent_builder_infra.providers",
        "agent_builder_infra.services",
        "agent_builder_infra.container",
        "agent_builder_infra.crud",
        "agent_builder_infra.orm",
        "agent_builder_infra.providers.object_storage",
        "agent_builder_infra.services.object_storage",
    ],
)
def test_package_imports(name):
    importlib.import_module(name)
