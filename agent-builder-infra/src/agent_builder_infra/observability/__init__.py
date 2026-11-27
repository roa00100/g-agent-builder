"""관측 — 구조적 로그(structlog)와 추적(OpenTelemetry)의 설정과 도구.

입구(runtime 의 명령줄·REST)가 맨 먼저 configure_logging·configure_tracing 을 부른다.
"""

from agent_builder_infra.observability.logging import (
    TRACE,
    LogFormat,
    Logger,
    LogLevel,
    configure_logging,
    get_logger,
    redact,
)
from agent_builder_infra.observability.tracing import (
    configure_tracing,
    set_attributes,
    span,
    traced,
)

__all__ = [
    "TRACE",
    "LogFormat",
    "LogLevel",
    "Logger",
    "configure_logging",
    "configure_tracing",
    "get_logger",
    "redact",
    "set_attributes",
    "span",
    "traced",
]
