"""모델 호출 REST 경로. 명령줄 묶음 model 과 같은 일을 한다.

POST /model/call                 본문은 core 의 ModelRequest, 응답은 ModelResponse
GET  /model/calls?limit=20       최근 호출 기록 (최근 것부터) — CallRecord 목록
GET  /model/calls/{request_id}   호출 기록 한 줄 — 없으면 404

실패는 이렇게 돌려준다:
  404  대응표에 없는 모델                 409  꺼 둔 모델
  422  요청 모양·모델이 받지 않는 내용    503  공급자 프로필이 없거나 꺼짐
  502  공급자 호출 실패 — 본문에 kind·retryable·detail·request_id
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from agent_builder_core.contracts.model import (
    CallLog,
    CallRecord,
    DisabledModel,
    ModelCallFailed,
    ModelRequest,
    ModelResponse,
    UnknownModel,
    UnknownProvider,
    UnsupportedInput,
)
from agent_builder_core.model import ModelGateway, UnresolvedSource
from agent_builder_runtime.container import get_call_log, get_model_gateway

router = APIRouter(prefix="/model", tags=["model"])

Gateway = Annotated[ModelGateway, Depends(get_model_gateway)]
Calls = Annotated[CallLog, Depends(get_call_log)]

# 기록 목록의 기본·최대 개수. 기본은 명령줄과 같고, 최대는 한 번에 돌려줄 만한 양이다.
DEFAULT_LIMIT = 20
MAX_LIMIT = 500


@router.post("/call", response_model=ModelResponse)
def call(request: ModelRequest, gateway: Gateway) -> ModelResponse | JSONResponse:
    try:
        return gateway.complete(request)
    except UnknownModel as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except DisabledModel as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except (UnsupportedInput, UnresolvedSource) as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)
        ) from error
    except UnknownProvider as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    except ModelCallFailed as error:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "kind": error.kind,
                "retryable": error.retryable,
                "detail": error.detail,
                "request_id": error.request_id,
            },
        )


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
            status.HTTP_404_NOT_FOUND, f"호출 기록이 없다: {request_id}"
        )
    return record
