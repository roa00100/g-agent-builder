"""환경변수와 .env 에서 읽는 설정."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from agent_builder_infra.observability.logging import LogFormat, LogLevel


def find_env_file() -> Path | None:
    """실행한 폴더에서 위로 올라가며 처음 만나는 .env.

    .env 는 저장소 루트에 하나 있다(docker compose 도 그것을 읽는다).
    agent-builder-infra/ 에서 실행해도 루트의 것을 찾게 하려는 것이다.
    컨테이너처럼 .env 가 없으면 None — 그때는 환경변수만 읽는다.
    """
    cwd = Path.cwd()
    for folder in [cwd, *cwd.parents]:
        candidate = folder / ".env"
        if candidate.is_file():
            return candidate
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # 같은 이름의 환경변수가 있으면 .env 보다 그쪽이 이긴다.
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        # .env 에 앱이 모르는 키가 있어도 오류로 보지 않고 넘긴다.
        extra="ignore",
        # `REDIS_PASSWORD=` 처럼 비워 둔 값은 빈 문자열이 아니라 None 으로 읽는다.
        env_parse_none_str="",
    )

    # PostgreSQL 접속 값. docker compose 가 같은 POSTGRES_* 로 계정과 DB 를 만든다 —
    # 값을 한 곳(.env)에만 적으려고 주소를 통째로 받지 않고 나눠 읽는다.
    postgres_user: str
    # SecretStr 이라 로그나 출력에 값이 찍히지 않는다.
    postgres_password: SecretStr
    # PC 에서는 127.0.0.1, 컨테이너 안에서는 compose 서비스 이름 db.
    postgres_host: str
    postgres_port: int
    postgres_db: str

    # Redis 접속 값. Postgres 와 같은 까닭으로 주소를 통째로 받지 않고 나눠 읽는다.
    # PC 에서는 127.0.0.1, 컨테이너 안에서는 compose 서비스 이름 redis.
    redis_host: str
    redis_port: int
    # Redis 안의 DB 번호 (0~15).
    redis_db: int
    # 비워 두면 None — 비밀번호 없이 붙는다.
    # 적으면 compose 의 Redis 도 같은 값을 요구한다.
    redis_password: SecretStr | None = None

    # 오브젝트 스토리지(SeaweedFS, S3 API) 접속 값. compose 와 같은 값을 쓴다.
    # PC 에서는 127.0.0.1, 컨테이너 안에서는 compose 서비스 이름 storage.
    storage_host: str
    storage_port: int
    storage_access_key: str
    storage_secret_key: SecretStr
    storage_bucket: str

    # 비밀 값(공급자 API 키 등)을 DB·캐시에 암호문으로 두는 마스터 키(Fernet).
    # 공급자 키·주소·대기 시간은 환경변수가 아니라 공급자 프로필(model_provider)에 있다.
    # 비밀을 다루지 않는 명령(마이그레이션 등)은 이 키 없이 돌아야 하므로 없어도 된다.
    # SecretStr 이라 로그나 출력에 값이 찍히지 않는다.
    secret_encryption_key: SecretStr | None = None

    # 관측. 로그 단계 — TRACE 는 오간 데이터 전체가 남으니 필요할 때만 켠다.
    log_level: LogLevel = "INFO"
    # console 은 사람이 읽기 쉬운 줄, json 은 수집기(Datadog 등)가 읽는 줄.
    log_format: LogFormat = "console"
    # 추적에서 이 프로그램을 부르는 이름.
    otel_service_name: str = "agent-builder"
    # 추적을 보낼 OTLP 주소 (예: 로컬 Jaeger http://127.0.0.1:4318).
    # 비우면 보내지 않는다.
    otel_exporter_otlp_endpoint: str | None = None

    @property
    def database_url(self) -> URL:
        """나눠 읽은 값으로 접속 주소를 조립한다. 드라이버는 psycopg 3.

        URL.create 가 비밀번호의 @ : / 같은 글자를 알아서 이스케이프한다.
        출력하면 비밀번호는 *** 로 가려진다.
        """
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def redis_url(self) -> str:
        """나눠 읽은 값으로 접속 주소를 조립한다.

        비밀번호가 있으면 redis://:비밀번호@호스트:포트/DB, 없으면 redis://호스트:포트/DB.
        비밀번호의 @ : / 같은 글자는 이스케이프한다.
        돌려주는 문자열에는 비밀번호가 그대로 들어 있다.
        출력하거나 로그에 남기지 않는다.
        """
        auth = ""
        if self.redis_password is not None:
            # safe="": / 까지 이스케이프해야 주소의 구분자와 헷갈리지 않는다.
            auth = f":{quote(self.redis_password.get_secret_value(), safe='')}@"
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def storage_endpoint_url(self) -> str:
        """S3 API 주소. 로컬 SeaweedFS 라 http 다."""
        return f"http://{self.storage_host}:{self.storage_port}"


@lru_cache
def get_settings() -> Settings:
    """설정을 한 번만 읽어 같은 객체를 돌려준다. 빠진 값이 있으면 여기서 실패한다."""
    return Settings()
