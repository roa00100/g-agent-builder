"""모델 호출 REST 경로. 명령줄 묶음 model 과 같은 일을 한다.

POST /model/call   본문은 core 의 ModelRequest, 응답은 ModelResponse

실패는 이렇게 돌려준다:
  404  대응표에 없는 모델                 409  꺼 둔 모델
  422  요청 모양·모델이 받지 않는 내용    503  공급자 프로필이 없거나 꺼짐
  502  공급자 호출 실패 — 본문에 kind·retryable·detail·request_id
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from agent_builder_core.contracts.model import (
    DisabledModel,
    ModelCallFailed,
    ModelRequest,
    ModelResponse,
    UnknownModel,
    UnknownProvider,
    UnsupportedInput,
)
from agent_builder_core.model import ModelGateway, UnresolvedSource
from agent_builder_runtime.container import get_model_gateway

router = APIRouter(prefix="/model", tags=["model"])

Gateway = Annotated[ModelGateway, Depends(get_model_gateway)]


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
