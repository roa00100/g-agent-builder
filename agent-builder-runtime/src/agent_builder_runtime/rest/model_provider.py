"""공급자 프로필 REST 경로. 명령줄 묶음 model-provider 와 같은 일을 한다.

GET    /model-provider                  전부 (키는 있음·없음만)
GET    /model-provider/{name}           한 줄 — 없으면 404
PUT    /model-provider/{name}           주소·대기 시간 넣거나 바꾸기 (켠 상태로)
PUT    /model-provider/{name}/api-key   API 키 넣기 — 암호화해 저장, 응답에 키는 없다
PATCH  /model-provider/{name}           켜고 끄기 — 본문 {"enabled": true|false}
DELETE /model-provider/{name}           지우기 — 없으면 404

인증이 아직 없어 서버는 기본으로 이 PC 에서만 붙는다. 키를 받는 경로가 있으므로
바깥에 열기 전에 인증부터 둔다.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from agent_builder_core.contracts.model import UnknownProvider
from agent_builder_runtime.container import get_provider_profiles
from agent_builder_runtime.repositories import (
    ProviderProfile,
    ProviderProfileRepository,
)

router = APIRouter(prefix="/model-provider", tags=["model-provider"])

Profiles = Annotated[ProviderProfileRepository, Depends(get_provider_profiles)]


class ProviderView(BaseModel):
    """밖으로 보이는 모양. 키·암호문은 없고 있음·없음만 있다."""

    name: str
    base_url: str
    timeout_seconds: float
    has_api_key: bool
    enabled: bool
    updated_at: datetime


class ProviderBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str = Field(min_length=1)
    timeout_seconds: float = Field(gt=0)


class ApiKeyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: str = Field(min_length=1)


class EnabledBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


@router.get("")
def list_profiles(profiles: Profiles) -> list[ProviderView]:
    return [_view(profile) for profile in profiles.list()]


@router.get("/{name}")
def get_profile(name: str, profiles: Profiles) -> ProviderView:
    return _view(_must_get(profiles, name))


@router.put("/{name}")
def put_profile(name: str, body: ProviderBody, profiles: Profiles) -> ProviderView:
    profiles.save(name, base_url=body.base_url, timeout_seconds=body.timeout_seconds)
    return _view(_must_get(profiles, name))


@router.put("/{name}/api-key", status_code=status.HTTP_204_NO_CONTENT)
def put_api_key(name: str, body: ApiKeyBody, profiles: Profiles) -> Response:
    try:
        profiles.set_api_key(name, body.api_key)
    except UnknownProvider as error:
        raise _not_found(name) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{name}")
def set_enabled(name: str, body: EnabledBody, profiles: Profiles) -> ProviderView:
    try:
        profiles.set_enabled(name, body.enabled)
    except UnknownProvider as error:
        raise _not_found(name) from error
    return _view(_must_get(profiles, name))


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(name: str, profiles: Profiles) -> Response:
    if not profiles.delete(name):
        raise _not_found(name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _must_get(profiles: ProviderProfileRepository, name: str) -> ProviderProfile:
    profile = profiles.get(name)
    if profile is None:
        raise _not_found(name)
    return profile


def _view(profile: ProviderProfile) -> ProviderView:
    return ProviderView(
        name=profile.name,
        base_url=profile.base_url,
        timeout_seconds=profile.timeout_seconds,
        has_api_key=profile.has_api_key,
        enabled=profile.enabled,
        updated_at=profile.updated_at,
    )


def _not_found(name: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"공급자 프로필이 없다: {name}")
