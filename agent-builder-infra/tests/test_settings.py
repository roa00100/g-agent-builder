import pytest
from pydantic import ValidationError

from agent_builder_infra.providers import RedisProvider
from agent_builder_infra.settings import Settings

REQUIRED = {
    "POSTGRES_USER": "u",
    "POSTGRES_PASSWORD": "p",
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "d",
    "REDIS_HOST": "127.0.0.1",
    "REDIS_PORT": "6379",
    "REDIS_DB": "0",
    "STORAGE_HOST": "127.0.0.1",
    "STORAGE_PORT": "8333",
    "STORAGE_ACCESS_KEY": "ak",
    "STORAGE_SECRET_KEY": "sk",
    "STORAGE_BUCKET": "b",
}


@pytest.fixture
def env(monkeypatch):
    """필수 값을 모두 채운다. 테스트가 하나씩 바꾸거나 지운다."""
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


def test_builds_database_url_from_parts(env):
    url = Settings(_env_file=None).database_url

    assert url.drivername == "postgresql+psycopg"
    assert (url.username, url.host, url.port, url.database) == (
        "u",
        "127.0.0.1",
        5432,
        "d",
    )
    assert url.password == "p"


def test_password_with_special_characters_survives(env):
    env.setenv("POSTGRES_PASSWORD", "p@ss:w/rd")

    url = Settings(_env_file=None).database_url

    assert url.password == "p@ss:w/rd"
    assert url.host == "127.0.0.1"


def test_password_is_hidden(env):
    env.setenv("POSTGRES_PASSWORD", "hidden-secret")
    settings = Settings(_env_file=None)

    assert "hidden-secret" not in repr(settings)
    assert "hidden-secret" not in str(settings.database_url)


def test_redis_url_without_password(env):
    env.delenv("REDIS_PASSWORD", raising=False)
    assert Settings(_env_file=None).redis_url == "redis://127.0.0.1:6379/0"

    # .env 에 `REDIS_PASSWORD=` 로 비워 둔 것도 비밀번호 없음이다.
    env.setenv("REDIS_PASSWORD", "")
    assert Settings(_env_file=None).redis_url == "redis://127.0.0.1:6379/0"


def test_redis_url_with_password(env):
    env.setenv("REDIS_PASSWORD", "pw")
    env.setenv("REDIS_DB", "3")

    assert Settings(_env_file=None).redis_url == "redis://:pw@127.0.0.1:6379/3"


def test_redis_password_with_special_characters_survives(env):
    env.setenv("REDIS_PASSWORD", "p@ss:w/rd")

    url = Settings(_env_file=None).redis_url
    # redis-py 가 주소를 풀었을 때 원래 비밀번호와 호스트가 그대로 나와야 한다.
    kwargs = RedisProvider(url).client.connection_pool.connection_kwargs

    assert kwargs["password"] == "p@ss:w/rd"
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["db"] == 0


def test_redis_password_is_hidden(env):
    env.setenv("REDIS_PASSWORD", "hidden-secret")

    assert "hidden-secret" not in repr(Settings(_env_file=None))


def test_storage_endpoint_and_hidden_secret(env):
    env.setenv("STORAGE_SECRET_KEY", "hidden-secret")
    settings = Settings(_env_file=None)

    assert settings.storage_endpoint_url == "http://127.0.0.1:8333"
    assert "hidden-secret" not in repr(settings)


def test_secret_encryption_key_is_optional_and_hidden(env):
    env.setenv("SECRET_ENCRYPTION_KEY", "")
    assert Settings(_env_file=None).secret_encryption_key is None

    env.setenv("SECRET_ENCRYPTION_KEY", "master-key")
    key = Settings(_env_file=None).secret_encryption_key
    assert key.get_secret_value() == "master-key"
    assert "master-key" not in repr(key)


def test_provider_settings_are_not_read_from_environment(env):
    # 공급자 키·대기 시간은 공급자 프로필(DB)에 있다. 설정에 없어야 한다.
    fields = Settings.model_fields

    assert "openrouter_api_key" not in fields
    assert "openrouter_timeout_seconds" not in fields


@pytest.mark.parametrize("missing", list(REQUIRED))
def test_missing_value_fails(env, missing):
    env.delenv(missing)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
