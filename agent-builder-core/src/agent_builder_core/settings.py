"""환경변수와 .env 에서 읽는 설정."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # 실행한 폴더의 .env 를 읽는다. 같은 이름의 환경변수가 있으면 그쪽이 이긴다.
        env_file=".env",
        env_file_encoding="utf-8",
        # .env 에는 docker compose 만 쓰는 값(POSTGRES_*)도 같이 있다.
        # 그래서 모르는 키를 오류로 보지 않고 넘긴다.
        extra="ignore",
        # `OPENROUTER_API_KEY=` 처럼 비워 둔 값은 빈 문자열이 아니라 None 으로 읽는다.
        env_parse_none_str="",
    )

    # 예: postgresql+psycopg://사용자:비밀번호@127.0.0.1:5432/DB이름
    database_url: str

    # 모델을 부르지 않는 명령(마이그레이션 등)은 키 없이 돌아야 하므로 없어도 된다.
    # SecretStr 이라 로그나 출력에 값이 찍히지 않는다. 꺼낼 때는 .get_secret_value()
    openrouter_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """설정을 한 번만 읽어 같은 객체를 돌려준다. 빠진 값이 있으면 여기서 실패한다."""
    return Settings()
