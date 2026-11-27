"""DB 공통 동작 — 트랜잭션·커서·SQL 직접 실행.

ORM 모델의 CRUD 는 crud.py 에 있다. 그쪽은 세션만 받으므로 이 서비스와 따로 둔다.
"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from psycopg import Cursor
from psycopg.rows import DictRow, dict_row
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from agent_builder_infra.providers.postgres import PostgresProvider

# SQL 의 :이름 자리에 들어갈 값.
Params = Mapping[str, Any]


class DbService:
    def __init__(self, provider: PostgresProvider) -> None:
        self._provider = provider

    # --- 트랜잭션 ---

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """트랜잭션 하나. 블록이 끝나면 커밋하고, 예외가 나면 롤백한다.

        with db.session_scope() as session:
            crud.create(session, Run, name="...")
        """
        with self._provider.session_factory.begin() as session:
            yield session

    # --- 커서 ---

    @contextmanager
    def cursor(self) -> Iterator[Cursor[DictRow]]:
        """psycopg 커서를 직접 쓴다. 행은 dict 로 나온다.

        파라미터는 psycopg 문법(%s, %(name)s)을 쓴다 — 아래 SQL 함수의 :name 과 다르다.
        블록이 끝나면 커밋하고, 예외가 나면 롤백한다.

        with db.cursor() as cur:
            cur.execute("select * from run where id = %(id)s", {"id": 1})
            row = cur.fetchone()
        """
        connection = self._provider.engine.raw_connection()
        try:
            with connection.driver_connection.cursor(row_factory=dict_row) as cur:
                yield cur
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            # 닫는 것이 아니라 풀로 돌려보낸다.
            connection.close()

    # --- SQL 직접 실행 ---
    #
    # session 을 넘기면 그 세션의 트랜잭션 안에서 돈다(커밋은 바깥이 한다).
    # 넘기지 않으면 호출마다 트랜잭션을 하나 열고, 끝나면 커밋한다.

    def fetch_all(
        self, sql: str, params: Params | None = None, *, session: Session | None = None
    ) -> list[dict[str, Any]]:
        """모든 행을 dict 목록으로."""
        with self._executor(session) as executor:
            result = executor.execute(text(sql), params or {})
            return [dict(row) for row in result.mappings()]

    def fetch_one(
        self, sql: str, params: Params | None = None, *, session: Session | None = None
    ) -> dict[str, Any] | None:
        """한 행을 dict 로. 없으면 None, 두 행 이상이면 오류."""
        with self._executor(session) as executor:
            row = executor.execute(text(sql), params or {}).mappings().one_or_none()
            return None if row is None else dict(row)

    def fetch_value(
        self, sql: str, params: Params | None = None, *, session: Session | None = None
    ) -> Any:
        """한 행의 첫 열 값. 없으면 None, 두 행 이상이면 오류. count(*) 같은 데 쓴다."""
        with self._executor(session) as executor:
            return executor.execute(text(sql), params or {}).scalar_one_or_none()

    def execute(
        self, sql: str, params: Params | None = None, *, session: Session | None = None
    ) -> int:
        """insert·update·delete 를 실행하고 바뀐 행 수를 돌려준다."""
        with self._executor(session) as executor:
            return executor.execute(text(sql), params or {}).rowcount

    @contextmanager
    def _executor(self, session: Session | None) -> Iterator[Session | Connection]:
        if session is not None:
            yield session
            return
        with self._provider.engine.begin() as connection:
            yield connection
