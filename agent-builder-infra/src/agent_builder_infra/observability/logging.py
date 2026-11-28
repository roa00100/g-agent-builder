"""구조적 로그 — structlog.

줄마다 trace_id·span_id 를 붙이고, 비밀은 단계와 상관없이 지운다.

단계(낮을수록 많이 남김):
  TRACE(5)  오간 데이터 전체 — 요청·응답 본문. 기본 꺼짐
            (사용자가 보낸 문장이 그대로 남는다)
  DEBUG     갈림길과 모양 — 캐시 적중, 연결을 새로 만들었는지, 고른 대기 시간
  INFO      흐름 요약 — 호출 끝, 모델, 토큰, 비용, 걸린 시간
  WARNING · ERROR
"""

import logging
import sys
from collections.abc import Mapping
from typing import Any, Literal

import structlog
from opentelemetry import trace

# 파이썬 logging 에 없는 단계. DEBUG(10)보다 아래.
TRACE = 5
logging.addLevelName(TRACE, "TRACE")

LogLevel = Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"]
LogFormat = Literal["console", "json"]

_LEVELS: dict[str, int] = {
    "TRACE": TRACE,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

# 이 낱말이 들어간 키의 값은 어느 단계에서도 남기지 않는다.
_SECRET_WORDS = ("api_key", "authorization", "secret", "password", "token_enc", "_enc")
REDACTED = "[REDACTED]"

_level = logging.INFO


def configure_logging(level: LogLevel, fmt: LogFormat) -> None:
    """프로세스에서 한 번 부른다. 다시 부르면 설정을 바꾼다(테스트용)."""
    global _level
    _level = _LEVELS[level]
    renderer = (
        structlog.processors.JSONRenderer(ensure_ascii=False)
        if fmt == "json"
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _apply_level_override,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_trace_ids,
            _redact_secrets,
            renderer,
        ],
        # TRACE 는 structlog 에 없는 단계라, 거르는 문턱은 DEBUG 에 두고
        # trace() 가 스스로 단계를 본다.
        wrapper_class=structlog.make_filtering_bound_logger(max(_level, logging.DEBUG)),
        # 쓸 때마다 그때의 sys.stderr 를 받는다. 설정 때의 것을 붙잡아 두면,
        # 바뀐 뒤(테스트의 출력 가로채기 등) 닫힌 파일에 쓰게 된다.
        logger_factory=lambda *_: structlog.PrintLogger(sys.stderr),
        cache_logger_on_first_use=False,
    )


class Logger:
    """trace() 를 더한 얇은 래퍼. 줄마다 logger 이름과 bind 한 값을 붙인다.

    줄을 남길 때마다 structlog 에서 그때의 설정을 받는다 — 모듈 맨 위에서 만들어 두어도
    나중의 configure_logging 을 따른다.
    """

    def __init__(self, name: str, fields: dict[str, Any] | None = None) -> None:
        self._name = name
        self._fields = fields or {}

    def trace(self, event: str, **fields: Any) -> None:
        if _level <= TRACE:
            self._emit("debug", event, _level="trace", **fields)

    def debug(self, event: str, **fields: Any) -> None:
        self._emit("debug", event, **fields)

    def info(self, event: str, **fields: Any) -> None:
        self._emit("info", event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit("warning", event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self._emit("error", event, **fields)

    def bind(self, **fields: Any) -> "Logger":
        return Logger(self._name, {**self._fields, **fields})

    def _emit(self, method: str, event: str, **fields: Any) -> None:
        log = structlog.get_logger()
        getattr(log, method)(event, logger=self._name, **self._fields, **fields)


def get_logger(name: str) -> Logger:
    return Logger(name)


def bind_context(**fields: Any) -> None:
    """지금 흐름(스레드·태스크)의 모든 로그 줄에 이 값을 붙인다.

    예: 셸의 세션 id·사용자.
    """
    structlog.contextvars.bind_contextvars(**fields)


def clear_context() -> None:
    structlog.contextvars.clear_contextvars()


def redact(value: Any) -> Any:
    """dict·list 를 훑어 비밀 키의 값을 지운다. 원본은 바꾸지 않는다."""
    if isinstance(value, Mapping):
        return {
            key: REDACTED if _is_secret(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(item) for item in value]
    return value


def _is_secret(key: str) -> bool:
    lowered = key.lower()
    return any(word in lowered for word in _SECRET_WORDS)


def _apply_level_override(_: Any, __: str, event_dict: dict) -> dict:
    override = event_dict.pop("_level", None)
    if override is not None:
        event_dict["level"] = override
    return event_dict


def _add_trace_ids(_: Any, __: str, event_dict: dict) -> dict:
    context = trace.get_current_span().get_span_context()
    if context.is_valid:
        event_dict["trace_id"] = format(context.trace_id, "032x")
        event_dict["span_id"] = format(context.span_id, "016x")
    return event_dict


def _redact_secrets(_: Any, __: str, event_dict: dict) -> dict:
    return redact(event_dict)
