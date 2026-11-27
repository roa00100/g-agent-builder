"""runtime 의 실행 설정 — 어느 모드로 돌지, REST 서버를 어디에 띄울지.

DB·Redis 같은 기술 구성의 설정은 infra 의 settings 에 있다. 같은 .env 를 읽는다.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from agent_builder_infra.settings import find_env_file

Profile = Literal["cli", "rest"]


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        # .env 에는 infra 의 값도 같이 있다. 모르는 키는 넘긴다.
        extra="ignore",
    )

    # 실행 모드. 기본은 cli — 터미널에서 짧게 쓰기 위해서다.
    # 서버로 띄울 때는 RUNTIME_PROFILE=rest 또는 --profile rest 로 명시한다.
    runtime_profile: Profile = "cli"

    # REST 서버가 듣는 주소. 기본은 이 PC 에서만 붙는 127.0.0.1 —
    # 아직 인증이 없으므로 바깥 네트워크에 열지 않는다.
    rest_host: str = "127.0.0.1"
    # 8000 은 uvicorn 의 기본 포트와 같다.
    rest_port: int = 8000


@lru_cache
def get_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings()
