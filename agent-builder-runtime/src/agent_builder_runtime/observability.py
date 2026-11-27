"""관측을 켜고, core 의 서비스를 span 으로 감싼다.

core 에는 추적 코드가 없다. 여기서 바깥을 감싸 어떤 클래스를 탔는지 남긴다.
입구(__main__·rest.create_app)가 맨 먼저 setup_observability() 를 부른다.
"""

from agent_builder_core.contracts.model import (
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
from agent_builder_infra.observability import (
    configure_logging,
    configure_tracing,
    get_logger,
    set_attributes,
    span,
)
from agent_builder_infra.settings import get_settings

log = get_logger("agent_builder_runtime.model")

# Gateway 가 보내기 전에 막는 것(ModelGateway.complete 의 설명과 같은 목록).
_REJECTED = (
    UnknownModel,
    DisabledModel,
    UnsupportedInput,
    UnresolvedSource,
    UnknownProvider,
)

_ready = False


def setup_observability() -> None:
    """로그와 추적을 켠다. 여러 번 불러도 한 번만 켠다 — cli 와 rest 가 같이 부른다."""
    global _ready
    if _ready:
        return
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    configure_tracing(settings.otel_service_name, settings.otel_exporter_otlp_endpoint)
    _ready = True


def report_record_error(record: CallRecord, error: Exception) -> None:
    """Gateway 가 기록에 실패했을 때 부른다. 호출은 살리고, 빠진 기록을 ERROR 로 남긴다.

    빠진 한 줄을 나중에 손으로 채울 수 있게 기록의 숫자를 함께 남긴다.
    """
    log.error(
        "model.call.record_failed",
        error=type(error).__name__,
        detail=str(error),
        record=record.model_dump(mode="json"),
    )


def trace_gateway(gateway: ModelGateway) -> ModelGateway:
    """Gateway 의 complete 를 바꿔 끼운다 — 호출 하나를 span 하나로, 끝을 INFO 한 줄로.

    span 에는 모양과 숫자만 둔다(모델·request_id·토큰·비용·종료 사유).
    오간 문장은 TRACE 로그에만 남긴다 — 추적은 밖(Jaeger·Datadog)으로 나가서.
    클래스는 그대로 ModelGateway 다.
    """
    send = gateway.complete

    def complete(request: ModelRequest) -> ModelResponse:
        ids = {"model": request.model, "request_id": request.request_id}
        with span(
            "ModelGateway.complete",
            **{"model.alias": request.model, "model.request_id": request.request_id},
        ):
            log.trace("model.request", request=request.model_dump(mode="json"))
            try:
                response = send(request)
            except ModelCallFailed as error:
                set_attributes(
                    **{"model.failure": error.kind, "model.retryable": error.retryable}
                )
                log.warning(
                    "model.call.failed",
                    **ids,
                    kind=error.kind,
                    retryable=error.retryable,
                    detail=error.detail,
                )
                raise
            except _REJECTED as error:
                # 보내기 전에 막힌 것 — 부른 쪽의 입력이나 설정 문제다.
                log.warning(
                    "model.call.rejected",
                    **ids,
                    error=type(error).__name__,
                    detail=str(error),
                )
                raise
            except Exception as error:
                # 그 밖의 것(ProviderMismatch 등)은 보낸 뒤에 나거나 구현의 결함이다.
                log.error(
                    "model.call.error",
                    **ids,
                    error=type(error).__name__,
                    detail=str(error),
                )
                raise
            usage = response.usage
            cost = None if usage.cost is None else str(usage.cost)
            summary = {
                "provider": response.provider,
                "provider_model": response.provider_model,
                "finish_reason": response.finish_reason,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cost": cost,
                "latency_ms": response.latency_ms,
            }
            set_attributes(**{f"model.{key}": value for key, value in summary.items()})
            log.info("model.call.done", **ids, **summary)
            log.trace("model.response", response=response.model_dump(mode="json"))
            return response

    gateway.complete = complete  # type: ignore[method-assign]
    return gateway
