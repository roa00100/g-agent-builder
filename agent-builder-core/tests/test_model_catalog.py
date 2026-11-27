"""모델 대응표 계약. 저장소 없이 메모리 구현으로 규칙을 확인한다."""

import pytest
from pydantic import ValidationError

from agent_builder_core.contracts.model import (
    DisabledModel,
    ModelCatalog,
    ModelSpec,
    UnknownModel,
    resolve_model,
)


class MemoryCatalog:
    """계약을 채우는 가장 작은 구현. infra 의 구현과 같은 계약을 따른다."""

    def __init__(self, *specs: ModelSpec) -> None:
        self._specs = {spec.name: spec for spec in specs}

    def get(self, name: str) -> ModelSpec | None:
        return self._specs.get(name)

    def upsert(self, spec: ModelSpec) -> None:
        self._specs[spec.name] = spec

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name not in self._specs:
            raise UnknownModel(name)
        self._specs[name] = self._specs[name].model_copy(update={"enabled": enabled})

    def delete(self, name: str) -> bool:
        return self._specs.pop(name, None) is not None

    def list(self) -> list[ModelSpec]:
        return [self._specs[name] for name in sorted(self._specs)]


def spec(name: str = "fast", **changes) -> ModelSpec:
    values = {
        "name": name,
        "provider": "openrouter",
        "provider_model": "vendor/model-a",
        "input_kinds": ("text",),
    }
    return ModelSpec(**{**values, **changes})


def test_resolve_returns_enabled_spec():
    assert resolve_model(MemoryCatalog(spec()), "fast") == spec()


def test_resolve_unknown_is_error():
    with pytest.raises(UnknownModel):
        resolve_model(MemoryCatalog(), "fast")


def test_resolve_disabled_is_error():
    with pytest.raises(DisabledModel):
        resolve_model(MemoryCatalog(spec(enabled=False)), "fast")


def test_memory_catalog_fills_contract():
    assert isinstance(MemoryCatalog(), ModelCatalog)


def test_object_missing_a_method_is_not_a_catalog():
    class ReadOnly:
        def get(self, name):
            return None

        def list(self):
            return []

    assert not isinstance(ReadOnly(), ModelCatalog)


def test_disable_then_resolve_is_error():
    catalog = MemoryCatalog(spec())

    catalog.set_enabled("fast", False)

    with pytest.raises(DisabledModel):
        resolve_model(catalog, "fast")


@pytest.mark.parametrize(
    "changes",
    [
        {"input_kinds": ()},
        {"input_kinds": ("video",)},
        {"name": ""},
        {"provider": ""},
        {"unknown_field": 1},
    ],
)
def test_spec_rejects_bad_shape(changes):
    with pytest.raises(ValidationError):
        spec(**changes)


def test_spec_is_frozen():
    with pytest.raises(ValidationError):
        spec().enabled = False
