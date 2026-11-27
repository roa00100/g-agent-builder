import pytest
from pydantic import ValidationError

from agent_builder_infra.settings import Settings

DB_URL = "postgresql+psycopg://u:p@127.0.0.1:5432/d"
REDIS_URL = "redis://127.0.0.1:6379/0"


def test_reads_urls_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("REDIS_URL", REDIS_URL)

    settings = Settings(_env_file=None)

    assert settings.database_url == DB_URL
    assert settings.redis_url == REDIS_URL


def test_openrouter_key_is_optional_and_hidden(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("REDIS_URL", REDIS_URL)

    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    assert Settings(_env_file=None).openrouter_api_key is None

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    key = Settings(_env_file=None).openrouter_api_key
    assert key.get_secret_value() == "test-key"
    assert "test-key" not in repr(key)


@pytest.mark.parametrize("missing", ["DATABASE_URL", "REDIS_URL"])
def test_missing_url_fails(monkeypatch, missing):
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("REDIS_URL", REDIS_URL)
    monkeypatch.delenv(missing)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
