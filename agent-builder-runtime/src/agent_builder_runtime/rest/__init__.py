"""rest 모드 — FastAPI 서버로 떠서 요청을 기다린다.

웹 프레임워크(FastAPI·uvicorn)는 이 패키지에서만 쓴다.
경로는 서비스(계약)를 부르기만 한다 — cli 모드와 같은 일을 다른 입구로 한다.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from agent_builder_runtime.container import close_all
from agent_builder_runtime.observability import setup_observability
from agent_builder_runtime.rest import model, model_catalog, model_provider
from agent_builder_runtime.settings import get_runtime_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # 서버가 끝날 때 연결 풀을 닫는다.
    close_all()


def create_app() -> FastAPI:
    # uvicorn 으로 직접 띄워도(__main__ 을 거치지 않아도) 관측이 켜지게 여기서도 부른다.
    setup_observability()
    app = FastAPI(title="agent-builder", lifespan=_lifespan)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """서버가 떠 있는지만 본다. DB·Redis 는 확인하지 않는다."""
        return {"status": "ok"}

    app.include_router(model.router)
    app.include_router(model_catalog.router)
    app.include_router(model_provider.router)
    # 요청 하나가 추적 하나의 뿌리 span 이 된다. /health 는 남기지 않는다.
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
    return app


def run() -> None:
    settings = get_runtime_settings()
    uvicorn.run(create_app(), host=settings.rest_host, port=settings.rest_port)
