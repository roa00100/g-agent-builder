"""REST 경로를 실제로 부른다. PostgreSQL·Redis 와 model_alias 테이블이 있어야 한다."""

import uuid

import pytest
from fastapi.testclient import TestClient

from agent_builder_runtime.container import close_all, get_model_catalog
from agent_builder_runtime.rest import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def name():
    name = f"test-{uuid.uuid4()}"
    yield name
    get_model_catalog().delete(name)
    close_all()


def body(name: str, **changes) -> dict:
    return {
        "name": name,
        "provider": "openrouter",
        "provider_model": "vendor/model-a",
        "input_kinds": ["text"],
        **changes,
    }


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_put_get_patch_delete(client, name):
    response = client.put(f"/model-catalog/{name}", json=body(name))
    assert response.status_code == 200

    got = client.get(f"/model-catalog/{name}").json()
    assert got["provider_model"] == "vendor/model-a"
    assert got["enabled"] is True
    assert got in client.get("/model-catalog").json()

    patched = client.patch(f"/model-catalog/{name}", json={"enabled": False})
    assert patched.json()["enabled"] is False

    assert client.delete(f"/model-catalog/{name}").status_code == 204
    assert client.get(f"/model-catalog/{name}").status_code == 404
    assert client.delete(f"/model-catalog/{name}").status_code == 404


def test_put_rejects_name_mismatch(client, name):
    response = client.put(f"/model-catalog/{name}", json=body("other"))

    assert response.status_code == 400


def test_put_rejects_bad_shape(client, name):
    # 계약(ModelSpec)이 모르는 종류와 모르는 필드는 거부된다.
    assert (
        client.put(
            f"/model-catalog/{name}", json=body(name, input_kinds=["video"])
        ).status_code
        == 422
    )
    assert (
        client.put(f"/model-catalog/{name}", json=body(name, extra=1)).status_code
        == 422
    )


def test_patch_unknown_is_404(client, name):
    response = client.patch(f"/model-catalog/{name}", json={"enabled": True})

    assert response.status_code == 404
