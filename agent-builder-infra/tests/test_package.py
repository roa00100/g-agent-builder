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
    ],
)
def test_package_imports(name):
    importlib.import_module(name)
