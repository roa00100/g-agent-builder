"""DB 연결. 엔진 하나와 세션 공장 하나를 프로세스 안에서 같이 쓴다."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from agent_builder_core.settings import get_settings


class Base(DeclarativeBase):
    """모든 테이블 모델의 부모. Alembic 이 이 MetaData 를 보고 변경을 찾는다."""


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """`with get_session_factory().begin() as session:` 으로 쓴다.

    블록이 끝나면 커밋하고, 예외가 나면 롤백한다.
    """
    return sessionmaker(get_engine())
