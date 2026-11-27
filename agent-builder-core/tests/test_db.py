"""실제 PostgreSQL 에 붙는다. 먼저 `docker compose up -d --wait` 로 DB 를 띄운다."""

from sqlalchemy import text

from agent_builder_core.db import get_engine, get_session_factory


def test_connects_to_postgres():
    with get_engine().connect() as connection:
        assert connection.dialect.name == "postgresql"
        assert connection.execute(text("select 1")).scalar_one() == 1


def test_session_runs_a_query():
    with get_session_factory().begin() as session:
        assert session.execute(text("select 1")).scalar_one() == 1
