"""모델 대응표 REST 경로. 명령줄 묶음 model-catalog 와 같은 일을 한다.

GET    /model-catalog              전부 (이름 순)
GET    /model-catalog/{name}       한 줄 — 없으면 404
PUT    /model-catalog/{name}       넣거나 바꾸기 — 본문은 ModelSpec
                                   (본문의 이름은 경로와 같아야 한다)
PATCH  /model-catalog/{name}       켜고 끄기 — 본문 {"enabled": true|false}
DELETE /model-catalog/{name}       지우기 — 없으면 404

여기는 core 의 계약(ModelCatalog)을 부르기만 한다. 캐시를 지우는 일 등은 구현이 한다.
요청·응답 본문은 core 의 ModelSpec 을 그대로 쓴다 — 모양을 따로 만들지 않는다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict

from agent_builder_core.contracts.model import ModelCatalog, ModelSpec, UnknownModel
from agent_builder_runtime.container import get_model_catalog

router = APIRouter(prefix="/model-catalog", tags=["model-catalog"])

Catalog = Annotated[ModelCatalog, Depends(get_model_catalog)]


class EnabledBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


@router.get("")
def list_specs(catalog: Catalog) -> list[ModelSpec]:
    return catalog.list()


@router.get("/{name}")
def get_spec(name: str, catalog: Catalog) -> ModelSpec:
    spec = catalog.get(name)
    if spec is None:
        raise _not_found(name)
    return spec


@router.put("/{name}")
def put_spec(name: str, spec: ModelSpec, catalog: Catalog) -> ModelSpec:
    if spec.name != name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"경로의 이름({name})과 본문의 이름({spec.name})이 다르다",
        )
    catalog.upsert(spec)
    return spec


@router.patch("/{name}")
def set_enabled(name: str, body: EnabledBody, catalog: Catalog) -> ModelSpec:
    try:
        catalog.set_enabled(name, body.enabled)
    except UnknownModel as error:
        raise _not_found(name) from error
    return catalog.get(name)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spec(name: str, catalog: Catalog) -> Response:
    if not catalog.delete(name):
        raise _not_found(name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _not_found(name: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"대응표에 없는 모델 이름: {name}")
