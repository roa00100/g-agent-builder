import importlib

import pytest


@pytest.mark.parametrize(
    "name",
    [
        "agent_builder_runtime",
        "agent_builder_runtime.__main__",
        "agent_builder_runtime.cli",
        "agent_builder_runtime.container",
        "agent_builder_runtime.cli.model_alias",
    ],
)
def test_package_imports(name):
    importlib.import_module(name)
