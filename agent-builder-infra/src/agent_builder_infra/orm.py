"""ORM 의 공통 부모.

접속(providers)과 따로 둔다 — 테이블 모델이 접속 코드를 import 하지 않게 하려는 것이다.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 테이블 모델의 부모. Alembic 이 이 MetaData 를 보고 변경을 찾는다."""
