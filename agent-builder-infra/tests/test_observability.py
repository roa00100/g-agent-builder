"""관측 — 로그 단계, 비밀 지우기, span 감싸기, SQL·Redis 자동 계측.

추적 설정(TracerProvider)은 프로세스에서 한 번만 정할 수 있어서, 이 모듈의 span 은
메모리 수집기 하나에 모은다. 테스트마다 비우고 본다.
"""

import json
from datetime import timedelta

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agent_builder_infra.observability import (
    configure_logging,
    configure_tracing,
    get_logger,
    redact,
    span,
    traced,
)
from agent_builder_infra.observability import tracing as tracing_module
from agent_builder_infra.providers import PostgresProvider, RedisProvider
from agent_builder_infra.services import DbService, RedisService
from agent_builder_infra.settings import get_settings

SPANS = InMemorySpanExporter()


@pytest.fixture(scope="module", autouse=True)
def tracing():
    # 다른 테스트가 먼저 켰을 수 있어 한 번 되돌린다 — 이 모듈의 수집기를 달기 위해서다.
    tracing_module._configured = False
    configure_tracing("test", None, extra_exporter=SPANS)


@pytest.fixture(autouse=True)
def clear_spans():
    SPANS.clear()


def lines(captured: str) -> list[dict]:
    return [json.loads(line) for line in captured.splitlines() if line.strip()]


# --- 로그 ---


def test_level_filters_and_trace_is_its_own_level(capsys):
    log = get_logger("t")
    configure_logging("INFO", "json")
    log.trace("a")
    log.debug("b")
    log.info("c")
    assert [line["event"] for line in lines(capsys.readouterr().err)] == ["c"]

    configure_logging("TRACE", "json")
    log.trace("a")
    log.debug("b")
    got = lines(capsys.readouterr().err)
    assert [(line["event"], line["level"]) for line in got] == [
        ("a", "trace"),
        ("b", "debug"),
    ]


def test_debug_level_hides_trace(capsys):
    configure_logging("DEBUG", "json")
    log = get_logger("t")
    log.trace("hidden")
    log.debug("shown")
    assert [line["event"] for line in lines(capsys.readouterr().err)] == ["shown"]


def test_logger_made_before_configure_follows_later_configure(capsys):
    # 모듈 맨 위에서 만든 로거도 나중 설정을 따라야 한다.
    log = get_logger("early")
    configure_logging("ERROR", "json")
    log.info("hidden")
    configure_logging("INFO", "json")
    log.info("shown")
    assert [line["event"] for line in lines(capsys.readouterr().err)] == ["shown"]


def test_secrets_are_redacted_at_every_level(capsys):
    configure_logging("TRACE", "json")
    get_logger("t").trace(
        "payload",
        api_key="sk-1",
        body={"headers": {"Authorization": "Bearer x"}, "api_key_enc": "gAAA"},
        password="p",
    )
    line = lines(capsys.readouterr().err)[0]
    assert line["api_key"] == "[REDACTED]"
    assert line["password"] == "[REDACTED]"
    assert line["body"]["headers"]["Authorization"] == "[REDACTED]"
    assert line["body"]["api_key_enc"] == "[REDACTED]"


def test_redact_keeps_ordinary_values_and_does_not_touch_original():
    original = {"model": "fast", "messages": [{"content": "안녕"}], "secret": "s"}
    assert redact(original) == {
        "model": "fast",
        "messages": [{"content": "안녕"}],
        "secret": "[REDACTED]",
    }
    assert original["secret"] == "s"


def test_log_lines_carry_trace_ids_inside_a_span(capsys):
    configure_logging("INFO", "json")
    with span("outer") as current:
        get_logger("t").info("inside")
    line = lines(capsys.readouterr().err)[0]
    context = current.get_span_context()
    assert line["trace_id"] == format(context.trace_id, "032x")
    assert line["span_id"] == format(context.span_id, "016x")


# --- span ---


class Thing:
    def work(self, secret: str) -> str:
        return secret.upper()

    def other(self) -> int:
        return 1


def test_traced_opens_span_per_method_and_keeps_class():
    thing = traced(Thing(), "Thing", ("work",))

    with span("root"):
        assert thing.work("k") == "K"
        assert thing.other() == 1

    assert isinstance(thing, Thing)
    names = [finished.name for finished in SPANS.get_finished_spans()]
    assert names == ["Thing.work", "root"]
    # 넘긴 값은 span 에 남지 않는다.
    work = SPANS.get_finished_spans()[0]
    assert "k" not in json.dumps(dict(work.attributes or {}))


def test_span_records_exception_and_reraises():
    with pytest.raises(ValueError), span("boom"):
        raise ValueError("x")

    finished = SPANS.get_finished_spans()[0]
    assert not finished.status.is_ok
    assert finished.events[0].name == "exception"


# --- 자동 계측 ---


def test_sql_and_redis_calls_become_child_spans():
    settings = get_settings()
    postgres = PostgresProvider(settings.database_url)
    redis_provider = RedisProvider(settings.redis_url)
    try:
        with span("root"):
            DbService(postgres).fetch_value("select 1")
            RedisService(redis_provider).set_str(
                "observability-test", "v", ttl=timedelta(seconds=5)
            )

        finished = {item.name: item for item in SPANS.get_finished_spans()}
        root = finished["root"]
        sql = finished["db SELECT"]
        assert sql.parent.span_id == root.context.span_id
        assert sql.attributes["db.statement"] == "select 1"
        redis_spans = [item for item in finished.values() if item.name == "SET"]
        assert redis_spans, list(finished)
        # 넣은 값은 span 에 남지 않는다.
        assert "v" not in str(redis_spans[0].attributes.get("db.statement"))
    finally:
        postgres.close()
        redis_provider.close()
