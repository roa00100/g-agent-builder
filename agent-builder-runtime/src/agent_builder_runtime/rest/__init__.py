"""rest 모드 — FastAPI 서버로 떠서 요청을 기다린다.

웹 프레임워크(FastAPI·uvicorn)는 이 패키지에서만 쓴다.
경로는 서비스(계약)를 부르기만 한다 — cli 모드와 같은 일을 다른 입구로 한다.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from agent_builder_runtime.container import close_all
from agent_builder_runtime.rest import model_catalog
from agent_builder_runtime.settings import get_runtime_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # 서버가 끝날 때 연결 풀을 닫는다.
    close_all()


def create_app() -> FastAPI:
    app = FastAPI(title="agent-builder", lifespan=_lifespan)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """서버가 떠 있는지만 본다. DB·Redis 는 확인하지 않는다."""
        return {"status": "ok"}

    app.include_router(model_catalog.router)
    return app


def run() -> None:
    settings = get_runtime_settings()
    uvicorn.run(create_app(), host=settings.rest_host, port=settings.rest_port)
