"""공급자 프로필의 명령줄과 REST. 실제 PostgreSQL·Redis 에 붙는다.

키는 어느 출력·응답에도 나오지 않아야 한다.
"""

import base64
import io
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from agent_builder_infra.settings import get_settings
from agent_builder_runtime import container
from agent_builder_runtime.__main__ import main
from agent_builder_runtime.rest import create_app

SECRET = "sk-or-test-secret-value"


@pytest.fixture(autouse=True)
def master_key(monkeypatch):
    """테스트마다 새 마스터 키로 조립한다."""
    monkeypatch.setenv(
        "SECRET_ENCRYPTION_KEY", base64.urlsafe_b64encode(os.urandom(32)).decode()
    )
    get_settings.cache_clear()
    container.close_all()
    yield
    container.close_all()
    get_settings.cache_clear()


@pytest.fixture
def name():
    name = f"test-{uuid.uuid4()}"
    yield name
    container.get_provider_profiles().delete(name)
    container.close_all()


def test_cli_flow(name, monkeypatch, capsys):
    base = ["model-provider"]
    assert (
        main([*base, "set", name, "--base-url", "https://x.dev", "--timeout", "45"])
        == 0
    )
    assert "키 없음" in capsys.readouterr().out

    monkeypatch.setattr("sys.stdin", io.StringIO(SECRET + "\n"))
    assert main([*base, "set-key", name, "--stdin"]) == 0
    assert main([*base, "show", name]) == 0
    shown = capsys.readouterr().out
    assert "api_key: 있음" in shown
    assert SECRET not in shown

    assert main([*base, "list"]) == 0
    listed = capsys.readouterr().out
    assert "45초" in listed
    assert SECRET not in listed

    assert main([*base, "disable", name]) == 0
    assert "꺼짐" in capsys.readouterr().out
    assert main([*base, "delete", name]) == 0
    assert main([*base, "show", name]) == 1


def test_cli_rejects_empty_key(name, monkeypatch):
    assert (
        main(
            [
                "model-provider",
                "set",
                name,
                "--base-url",
                "https://x.dev",
                "--timeout",
                "45",
            ]
        )
        == 0
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("\n"))

    assert main(["model-provider", "set-key", name, "--stdin"]) == 2


def test_cli_timeout_is_required(name):
    with pytest.raises(SystemExit):
        main(["model-provider", "set", name, "--base-url", "https://x.dev"])


def test_rest_flow(name):
    with TestClient(create_app()) as client:
        put = client.put(
            f"/model-provider/{name}",
            json={"base_url": "https://x.dev", "timeout_seconds": 45},
        )
        assert put.status_code == 200
        assert put.json()["has_api_key"] is False

        key = client.put(f"/model-provider/{name}/api-key", json={"api_key": SECRET})
        assert key.status_code == 204
        assert key.content == b""

        got = client.get(f"/model-provider/{name}")
        assert got.json()["has_api_key"] is True
        assert SECRET not in got.text
        assert "api_key_enc" not in got.text
        assert SECRET not in client.get("/model-provider").text

        patched = client.patch(f"/model-provider/{name}", json={"enabled": False})
        assert patched.json()["enabled"] is False

        assert client.delete(f"/model-provider/{name}").status_code == 204
        assert client.get(f"/model-provider/{name}").status_code == 404
        assert (
            client.put(f"/model-provider/{name}/api-key", json={"api_key": "k"})
        ).status_code == 404


def test_rest_rejects_bad_body(name):
    with TestClient(create_app()) as client:
        bad = client.put(
            f"/model-provider/{name}",
            json={"base_url": "https://x.dev", "timeout_seconds": 0},
        )
        assert bad.status_code == 422
