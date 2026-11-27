import pytest
from pydantic import ValidationError

from agent_builder_core.settings import Settings


def test_reads_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@127.0.0.1:5432/d")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://u:p@127.0.0.1:5432/d"


def test_openrouter_key_is_optional_and_hidden(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@127.0.0.1:5432/d")

    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    assert Settings(_env_file=None).openrouter_api_key is None

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    key = Settings(_env_file=None).openrouter_api_key
    assert key.get_secret_value() == "test-key"
    assert "test-key" not in repr(key)


def test_missing_database_url_fails(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
