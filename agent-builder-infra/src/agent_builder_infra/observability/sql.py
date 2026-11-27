"""SQL 실행마다 span 하나 — SQLAlchemy 이벤트로 직접 건다.

공식 계측(opentelemetry-instrumentation-sqlalchemy 0.66b2)을 쓰지 않는 까닭:
SQLAlchemy 2.1 미만만 받고, 켜면 asyncio 모듈(greenlet 필요)까지 불러온다.
이벤트(실행 전·후·오류)는 SQLAlchemy 의 공개 API 라 버전을 덜 탄다.

남기는 것: SQL 문(자리표시자 그대로). 넘긴 값(parameters)은 남기지 않는다 —
API 키 암호문 같은 값이 들어갈 수 있어서.
"""

from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from sqlalchemy import event
from sqlalchemy.engine import Engine

_tracer = trace.get_tracer("agent_builder.sql")
_SPAN = "_agent_builder_span"
_installed = False


def instrument_sql() -> None:
    """모든 Engine 에 건다(클래스 단위 이벤트). 여러 번 불러도 한 번만 건다."""
    global _installed
    if _installed:
        return
    event.listen(Engine, "before_cursor_execute", _before)
    event.listen(Engine, "after_cursor_execute", _after)
    event.listen(Engine, "handle_error", _error)
    _installed = True


def _before(
    conn: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    operation = (
        statement.lstrip().split(None, 1)[0].upper() if statement.strip() else "SQL"
    )
    span = _tracer.start_span(
        f"db {operation}",
        kind=trace.SpanKind.CLIENT,
        attributes={
            "db.system": conn.engine.dialect.name,
            "db.operation": operation,
            "db.statement": statement,
            "db.executemany": executemany,
        },
    )
    setattr(context, _SPAN, span)


def _after(
    conn: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    span = getattr(context, _SPAN, None)
    if span is None:
        return
    if cursor is not None and cursor.rowcount is not None and cursor.rowcount >= 0:
        span.set_attribute("db.rowcount", cursor.rowcount)
    span.end()


def _error(exception_context: Any) -> None:
    span = getattr(exception_context.execution_context, _SPAN, None)
    if span is None:
        return
    span.record_exception(exception_context.original_exception)
    span.set_status(
        Status(StatusCode.ERROR, type(exception_context.original_exception).__name__)
    )
    span.end()
