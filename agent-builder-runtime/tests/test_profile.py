"""프로필로 모드를 고르는 입구."""

import pytest

from agent_builder_runtime.__main__ import _pick_profile, main
from agent_builder_runtime.settings import get_runtime_settings


@pytest.fixture(autouse=True)
def fresh_settings(monkeypatch):
    """테스트마다 환경변수를 비우고 설정을 새로 읽게 한다."""
    monkeypatch.delenv("RUNTIME_PROFILE", raising=False)
    get_runtime_settings.cache_clear()
    yield monkeypatch
    get_runtime_settings.cache_clear()


def test_default_is_cli(monkeypatch):
    # .env 에 RUNTIME_PROFILE 이 적혀 있어도 이 테스트가 흔들리지 않게 cli 로 고정한다.
    monkeypatch.setattr(get_runtime_settings(), "runtime_profile", "cli", raising=False)
    assert _pick_profile(["model-catalog", "list"]) == (
        "cli",
        ["model-catalog", "list"],
    )


def test_env_picks_profile(monkeypatch):
    monkeypatch.setenv("RUNTIME_PROFILE", "rest")
    get_runtime_settings.cache_clear()

    assert _pick_profile([]) == ("rest", [])


def test_flag_beats_env(monkeypatch):
    monkeypatch.setenv("RUNTIME_PROFILE", "rest")
    get_runtime_settings.cache_clear()

    assert _pick_profile(["--profile", "cli", "model-catalog", "list"]) == (
        "cli",
        ["model-catalog", "list"],
    )


def test_unknown_profile_is_rejected():
    with pytest.raises(SystemExit):
        _pick_profile(["--profile", "batch"])


def test_rest_mode_takes_no_arguments(capsys):
    assert main(["--profile", "rest", "model-catalog", "list"]) == 2
    assert "rest 모드는 인자를 받지 않는다" in capsys.readouterr().err
