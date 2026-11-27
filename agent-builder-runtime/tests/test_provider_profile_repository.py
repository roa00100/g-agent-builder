"""공급자 프로필 저장소. 실제 PostgreSQL·Redis 에 붙는다(alembic upgrade head)."""

import base64
import os
import uuid

import pytest

from agent_builder_core.contracts.model import UnknownProvider
from agent_builder_infra.services import CipherError, FernetCipher, redis_key
from agent_builder_runtime.repositories import (
    MissingApiKey,
    ProviderProfile,
    ProviderProfileRepository,
)


def new_key() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


@pytest.fixture
def cipher():
    return FernetCipher(new_key())


@pytest.fixture
def profiles(db, redis_service, cipher):
    return ProviderProfileRepository(db, redis_service, lambda: cipher)


@pytest.fixture
def name(db, redis_service):
    name = f"test-{uuid.uuid4()}"
    yield name
    db.execute("delete from model_provider where name = :n", {"n": name})
    redis_service.delete(redis_key("model_provider", name))


def test_save_then_get(profiles, name):
    profiles.save(name, base_url="https://openrouter.ai/api/v1", timeout_seconds=60)

    profile = profiles.get(name)

    assert profile.base_url == "https://openrouter.ai/api/v1"
    assert profile.timeout_seconds == 60
    assert profile.enabled is True
    assert profile.has_api_key is False
    assert profile in profiles.list()


def test_unknown_profile(profiles, name):
    assert profiles.get(name) is None
    with pytest.raises(UnknownProvider):
        profiles.set_api_key(name, "k")
    with pytest.raises(UnknownProvider):
        profiles.set_enabled(name, False)
    assert profiles.delete(name) is False


def test_api_key_is_never_stored_in_plaintext(profiles, name, db, redis_service):
    profiles.save(name, base_url="https://x.dev", timeout_seconds=60)
    profiles.set_api_key(name, "sk-or-plain-secret")

    stored = db.fetch_value(
        "select api_key_enc from model_provider where name = :n", {"n": name}
    )
    profile = profiles.get(name)  # 캐시를 채운다
    cached = redis_service.get_str(redis_key("model_provider", name))

    assert b"sk-or-plain-secret" not in bytes(stored)
    assert "sk-or-plain-secret" not in cached
    assert profile.has_api_key is True
    assert profiles.api_key(profile) == "sk-or-plain-secret"


def test_cached_profile_round_trips_ciphertext(profiles, name, redis_service):
    profiles.save(name, base_url="https://x.dev", timeout_seconds=60)
    profiles.set_api_key(name, "k-1")
    profiles.get(name)

    cached = redis_service.get_model(redis_key("model_provider", name), ProviderProfile)

    assert profiles.api_key(cached) == "k-1"


def test_missing_key(profiles, name):
    profiles.save(name, base_url="https://x.dev", timeout_seconds=60)

    with pytest.raises(MissingApiKey):
        profiles.api_key(profiles.get(name))


def test_save_keeps_existing_key_and_clears_cache(profiles, name):
    profiles.save(name, base_url="https://x.dev", timeout_seconds=60)
    profiles.set_api_key(name, "k-1")
    before = profiles.get(name)

    profiles.save(name, base_url="https://y.dev", timeout_seconds=90)
    after = profiles.get(name)

    assert after.base_url == "https://y.dev"
    assert after.timeout_seconds == 90
    assert profiles.api_key(after) == "k-1"
    # 프로필이 바뀌면 updated_at 도 바뀐다 — 연결을 새로 만드는 신호다.
    assert after.updated_at > before.updated_at


def test_set_enabled_and_delete(profiles, name):
    profiles.save(name, base_url="https://x.dev", timeout_seconds=60)
    profiles.get(name)

    profiles.set_enabled(name, False)
    assert profiles.get(name).enabled is False

    assert profiles.delete(name) is True
    assert profiles.get(name) is None


def test_empty_key_is_rejected(profiles, name):
    profiles.save(name, base_url="https://x.dev", timeout_seconds=60)

    with pytest.raises(ValueError):
        profiles.set_api_key(name, "")


def test_other_master_key_cannot_read(db, redis_service, profiles, name):
    profiles.save(name, base_url="https://x.dev", timeout_seconds=60)
    profiles.set_api_key(name, "k-1")
    other_cipher = FernetCipher(new_key())
    other = ProviderProfileRepository(db, redis_service, lambda: other_cipher)

    with pytest.raises(CipherError):
        other.api_key(other.get(name))


def test_listing_needs_no_master_key(db, redis_service, profiles, name):
    profiles.save(name, base_url="https://x.dev", timeout_seconds=60)

    def no_cipher():
        raise RuntimeError("SECRET_ENCRYPTION_KEY 가 없다")

    keyless = ProviderProfileRepository(db, redis_service, no_cipher)

    assert any(profile.name == name for profile in keyless.list())
    assert keyless.get(name).name == name
