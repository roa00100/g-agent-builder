"""공급자 연결 관리 — 프로필이 바뀌면 연결을 새로 만든다. 가짜 프로필로 돈다."""

from datetime import UTC, datetime, timedelta

import pytest

from agent_builder_core.contracts.model import UnknownProvider
from agent_builder_runtime.model_providers import ProviderConnections
from agent_builder_runtime.repositories import MissingApiKey, ProviderProfile

T0 = datetime(2026, 1, 1, tzinfo=UTC)


class FakeProfiles:
    def __init__(self) -> None:
        self.profiles: dict[str, ProviderProfile] = {}

    def put(self, **changes) -> None:
        values = {
            "name": "openrouter",
            "base_url": "https://x.dev",
            "api_key_enc": b"enc",
            "timeout_seconds": 60,
            "enabled": True,
            "updated_at": T0,
        }
        profile = ProviderProfile(**{**values, **changes})
        self.profiles[profile.name] = profile

    def get(self, name: str) -> ProviderProfile | None:
        return self.profiles.get(name)

    def api_key(self, profile: ProviderProfile) -> str:
        if profile.api_key_enc is None:
            raise MissingApiKey("키 없음")
        return f"key-for-{profile.base_url}"


class FakeConnection:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.closed = False

    def chat(self, payload, timeout_seconds):
        return {}

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def profiles():
    fake = FakeProfiles()
    fake.put()
    return fake


@pytest.fixture
def made():
    return []


@pytest.fixture
def connections(profiles, made):
    def connect(base_url: str, api_key: str) -> FakeConnection:
        connection = FakeConnection(base_url, api_key)
        made.append(connection)
        return connection

    return ProviderConnections(profiles, connect)


def test_builds_from_profile(connections, made):
    got = connections.get("openrouter")

    assert got.timeout_seconds == 60
    assert got.connection is made[0]
    assert made[0].api_key == "key-for-https://x.dev"


def test_reuses_while_profile_unchanged(connections, made):
    connections.get("openrouter")
    connections.get("openrouter")

    assert len(made) == 1


def test_rebuilds_and_closes_old_when_profile_changes(connections, profiles, made):
    connections.get("openrouter")
    profiles.put(base_url="https://y.dev", updated_at=T0 + timedelta(seconds=1))

    got = connections.get("openrouter")

    assert len(made) == 2
    assert made[0].closed is True
    assert got.connection.base_url == "https://y.dev"


def test_timeout_follows_profile_without_rebuild(connections, profiles, made):
    # 대기 시간만 바뀌어도 updated_at 이 바뀌므로 새 값을 쓴다.
    connections.get("openrouter")
    profiles.put(timeout_seconds=90, updated_at=T0 + timedelta(seconds=1))

    assert connections.get("openrouter").timeout_seconds == 90


@pytest.mark.parametrize("change", [{"enabled": False}, {"name": "other"}])
def test_missing_or_disabled_profile(connections, profiles, change):
    profiles.profiles.clear()
    profiles.put(**change)

    with pytest.raises(UnknownProvider):
        connections.get("openrouter")


def test_missing_key(connections, profiles):
    profiles.put(api_key_enc=None)

    with pytest.raises(MissingApiKey):
        connections.get("openrouter")


def test_close_all(connections, made):
    connections.get("openrouter")

    connections.close_all()

    assert made[0].closed is True
