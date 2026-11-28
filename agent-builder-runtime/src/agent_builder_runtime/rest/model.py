"""모델 호출 REST 경로. 명령줄 묶음 model 과 같은 일을 한다.

POST /model/call                 본문은 core 의 ModelRequest, 응답은 ModelResponse
GET  /model/calls?limit=20       최근 호출 기록 (최근 것부터) — CallRecord 목록
GET  /model/calls/{request_id}   호출 기록 한 줄 — 없으면 404
GET  /model/calls/{request_id}/bodies/{name}   남긴 본문 하나 — 없으면 404

실패는 이렇게 돌려준다. 본문에는 늘 사람이 읽는 message·facts·next 가 있고
(명령줄과 같은 문장 — failure_text), 기계가 읽는 칸은 경우마다 더한다.
  404  대응표에 없는 모델                 409  꺼 둔 모델
  422  요청 모양·모델이 받지 않는 내용    503  공급자를 부를 수 없음·마스터 키 문제
  502  공급자 호출 실패 — kind·retryable·sent·request_id
  503  기록을 남기지 못해 결과를 쓰지 않음 — kind=not_recorded·stage·sent·request_id
  500  공급자 구현의 결함(응답이 요청과 맞지 않음) — kind=provider_mismatch·request_id
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from agent_builder_core.contracts.model import (
    BodyName,
    CallLog,
    CallNotRecorded,
    CallRecord,
    DisabledModel,
    ModelCallFailed,
    ModelRequest,
    ModelResponse,
    UnknownModel,
    UnknownProvider,
    UnsupportedInput,
)
from agent_builder_core.model import ModelGateway, ProviderMismatch, UnresolvedSource
from agent_builder_infra.services import CipherError
from agent_builder_runtime.container import (
    MissingMasterKey,
    get_call_log,
    get_model_gateway,
)
from agent_builder_runtime.failure_text import explain, no_call_body, no_call_record
from agent_builder_runtime.repositories import MissingApiKey

router = APIRouter(prefix="/model", tags=["model"])

Gateway = Annotated[ModelGateway, Depends(get_model_gateway)]
Calls = Annotated[CallLog, Depends(get_call_log)]

# 기록 목록의 기본·최대 개수. 기본은 명령줄과 같고, 최대는 한 번에 돌려줄 만한 양이다.
DEFAULT_LIMIT = 20
MAX_LIMIT = 500

# 보내기 전에 막힌 실패 → HTTP 상태.
_BLOCKED: tuple[tuple[type[Exception], int], ...] = (
    (UnknownModel, status.HTTP_404_NOT_FOUND),
    (DisabledModel, status.HTTP_409_CONFLICT),
    (UnsupportedInput, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (UnresolvedSource, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (UnknownProvider, status.HTTP_503_SERVICE_UNAVAILABLE),
    (MissingMasterKey, status.HTTP_503_SERVICE_UNAVAILABLE),
    (CipherError, status.HTTP_503_SERVICE_UNAVAILABLE),
    (MissingApiKey, status.HTTP_503_SERVICE_UNAVAILABLE),
)


@router.post("/call", response_model=ModelResponse)
def call(request: ModelRequest, gateway: Gateway) -> ModelResponse | JSONResponse:
    try:
        return gateway.complete(request)
    except ModelCallFailed as error:
        return _failure(
            status.HTTP_502_BAD_GATEWAY,
            error,
            kind=error.kind,
            retryable=error.retryable,
            sent=error.sent,
            detail=error.detail,
            request_id=error.request_id,
        )
    except CallNotRecorded as error:
        return _failure(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error,
            kind="not_recorded",
            stage=error.stage,
            sent=error.sent,
            detail=error.detail,
            request_id=error.request_id,
        )
    except ProviderMismatch as error:
        return _failure(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error,
            kind="provider_mismatch",
            request_id=error.request_id,
        )
    except tuple(kind for kind, _ in _BLOCKED) as error:
        code = next(code for kind, code in _BLOCKED if isinstance(error, kind))
        raise HTTPException(code, explain(error, "call").as_dict()) from error


@router.get("/calls")
def list_calls(
    calls: Calls, limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT
) -> list[CallRecord]:
    return calls.list(limit)


@router.get("/calls/{request_id}")
def get_call(request_id: str, calls: Calls) -> CallRecord:
    record = calls.get(request_id)
    if record is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, no_call_record(request_id).as_dict()
        )
    return record


@router.get("/calls/{request_id}/bodies/{name}")
def get_call_body(request_id: str, name: BodyName, calls: Calls) -> dict:
    record = calls.get(request_id)
    key = None if record is None else record.bodies.get(name)
    body = None if key is None else calls.read_body(key)
    if body is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, no_call_body(request_id, name).as_dict()
        )
    return body


def _failure(code: int, error: Exception, **fields: object) -> JSONResponse:
    return JSONResponse(
        status_code=code, content={**fields, **explain(error, "call").as_dict()}
    )
