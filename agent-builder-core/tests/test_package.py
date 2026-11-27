import importlib

import pytest


@pytest.mark.parametrize(
    "name",
    [
        "agent_builder_core",
        "agent_builder_core.workflow",
        "agent_builder_core.run",
        "agent_builder_core.assist",
    ],
)
def test_package_imports(name):
    importlib.import_module(name)
