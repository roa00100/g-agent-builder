"""추적 — OpenTelemetry. 요청 하나가 어떤 클래스를 타고 갔는지 span 으로 남긴다.

내보낼 곳(OTLP 주소)을 주면 거기로 보낸다 — 로컬은 Jaeger, 나중에는 Datadog Agent.
주지 않아도 span 은 만들어져, 로그 줄마다 trace_id 가 붙는다.
DB·Redis·HTTP·S3 호출은 자동 계측으로 잡힌다.
"""

import functools
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.httpx import HTTPX2ClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)

from agent_builder_infra.observability.sql import instrument_sql

_tracer = trace.get_tracer("agent_builder")
_configured = False


def configure_tracing(
    service_name: str,
    otlp_endpoint: str | None,
    extra_exporter: SpanExporter | None = None,
) -> None:
    """프로세스에서 한 번만 효과가 있다(OpenTelemetry 의 전역 설정이 한 번뿐이라서).

    extra_exporter: 테스트가 span 을 메모리에 모을 때 쓴다.
    """
    global _configured
    if _configured:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if otlp_endpoint:
        # 모아서 보낸다. 프로세스가 끝날 때 남은 것을 비운다(SDK 가 atexit 에 건다).
        exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
    if extra_exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(extra_exporter))
    trace.set_tracer_provider(provider)
    # 연결을 만들기 전에 켜야 그 연결이 잡힌다 — 입구에서 맨 먼저 부른다.
    instrument_sql()
    RedisInstrumentor().instrument()
    # openai SDK(3.x)는 httpx 가 아니라 httpx2 로 보낸다 — 그쪽을 계측한다.
    HTTPX2ClientInstrumentor().instrument()
    BotocoreInstrumentor().instrument()
    _configured = True


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[trace.Span]:
    """span 하나를 연다. 안에서 난 예외는 span 에 기록되고 그대로 올라간다."""
    with _tracer.start_as_current_span(name, attributes=_clean(attributes)) as current:
        yield current


def set_attributes(**attributes: Any) -> None:
    """지금 span 에 값을 더한다. 비밀은 넣지 않는다 — 넣는 쪽이 고른다."""
    trace.get_current_span().set_attributes(_clean(attributes))


def traced[T](target: T, name: str, methods: Iterable[str]) -> T:
    """target 의 메서드를 부를 때마다 「name.메서드」 span 을 열게 바꾼다.

    바꾼 target 을 그대로 돌려준다.

    감싼 객체를 따로 만들지 않고 그 객체의 메서드를 바꿔 끼운다 — 클래스가 그대로라
    isinstance(계약) 확인도 그대로 맞는다(Protocol 확인은 __getattr__ 을 보지 않는다).
    넘긴 값은 span 에 남기지 않는다.
    """
    for method in methods:
        original = getattr(target, method)
        setattr(target, method, _wrap(original, f"{name}.{method}"))
    return target


def _wrap(function: Callable[..., Any], span_name: str) -> Callable[..., Any]:
    @functools.wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with span(span_name):
            return function(*args, **kwargs)

    return wrapper


def _clean(attributes: dict[str, Any]) -> dict[str, Any]:
    # OpenTelemetry 속성은 str·bool·int·float(와 그 목록)만 받는다. None 은 뺀다.
    cleaned: dict[str, Any] = {}
    for key, value in attributes.items():
        if value is None:
            continue
        cleaned[key] = (
            value if isinstance(value, str | bool | int | float) else str(value)
        )
    return cleaned
