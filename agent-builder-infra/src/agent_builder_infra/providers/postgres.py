from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker


class PostgresProvider:
    """PostgreSQL 접속. 엔진(연결 풀)과 세션 공장을 갖는다.

    연결은 처음 쓸 때 만들어진다. 만드는 것만으로는 DB 에 붙지 않는다.
    """

    def __init__(self, url: str | URL) -> None:
        self.engine: Engine = create_engine(url)
        self.session_factory: sessionmaker[Session] = sessionmaker(self.engine)

    def ping(self) -> bool:
        """붙으면 True. 붙지 못하면 False 가 아니라 예외가 난다 — 까닭을 잃지 않는다."""
        with self.engine.connect() as connection:
            connection.execute(text("select 1"))
        return True

    def close(self) -> None:
        """연결 풀을 비운다. 그 뒤에 다시 쓰면 새 연결을 만든다."""
        self.engine.dispose()
