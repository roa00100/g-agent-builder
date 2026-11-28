"""공급자 연결 관리 — 프로필을 읽어 연결점을 만들고, 프로필이 바뀌면 새로 만든다.

키와 주소가 DB 에 있으므로 프로세스가 시작할 때 한 번 만들고 끝낼 수 없다.
프로필의 updated_at 이 달라지면(키를 바꾸거나 주소를 고치면) 옛 연결을 닫고 새로 만든다.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from agent_builder_core.contracts.model import UnknownProvider
from agent_builder_infra.observability import get_logger
from agent_builder_runtime.repositories.provider_profile import ProviderProfile

log = get_logger(__name__)


class Connection(Protocol):
    """infra 의 연결점(예: OpenRouterClient)이 채운다."""

    def chat(
        self, payload: dict[str, Any], timeout_seconds: float
    ) -> dict[str, Any]: ...


class Profiles(Protocol):
    """ProviderProfileRepository 가 채운다."""

    def get(self, name: str) -> ProviderProfile | None: ...

    def api_key(self, profile: ProviderProfile) -> str: ...


@dataclass(frozen=True)
class ProviderConnection:
    connection: Connection
    # 공급자 프로필의 기본 대기 시간. 모델별 덮어쓰기는 부르는 쪽이 고른다.
    timeout_seconds: float
    # 그때의 설정 사본(추적)에 남기는 값 — 어느 주소로, 프로필의 어느 판으로 보냈나.
    base_url: str
    profile_updated_at: datetime


class ProviderConnections:
    def __init__(
        self, profiles: Profiles, connect: Callable[[str, str], Connection]
    ) -> None:
        """connect(base_url, api_key) 가 연결점 하나를 만든다."""
        self._profiles = profiles
        self._connect = connect
        self._open: dict[str, tuple[datetime, Connection]] = {}

    def get(self, name: str) -> ProviderConnection:
        """없거나 꺼진 공급자면 UnknownProvider, 키가 없으면 MissingApiKey."""
        profile = self._profiles.get(name)
        if profile is None:
            raise UnknownProvider(name, "no_profile")
        if not profile.enabled:
            raise UnknownProvider(name, "disabled")
        opened = self._open.get(name)
        if opened is None or opened[0] != profile.updated_at:
            # 처음 여는지, 프로필이 바뀌어 다시 여는지 남긴다.
            log.debug(
                "provider.connection.open",
                provider=name,
                reason="first" if opened is None else "profile_changed",
            )
            if opened is not None:
                _close(opened[1])
            connection = self._connect(
                profile.base_url, self._profiles.api_key(profile)
            )
            self._open[name] = (profile.updated_at, connection)
        return ProviderConnection(
            self._open[name][1],
            timeout_seconds=profile.timeout_seconds,
            base_url=profile.base_url,
            profile_updated_at=profile.updated_at,
        )

    def close_all(self) -> None:
        for _, connection in self._open.values():
            _close(connection)
        self._open.clear()


def _close(connection: Connection) -> None:
    close = getattr(connection, "close", None)
    if close is not None:
        close()
