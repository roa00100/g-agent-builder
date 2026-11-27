"""ORM 모델의 공통 CRUD.

세션은 부르는 쪽이 넘긴다 — 트랜잭션의 경계(언제 커밋하나)는 부르는 쪽이 정한다.
쓰기 함수는 flush 까지만 한다. DB 가 채우는 값(id 등)은 바로 보이지만,
커밋은 하지 않는다.

with db.session_scope() as session:
    run = crud.create(session, Run, name="주간 보고")
    crud.update(session, run, status="done")
"""

from typing import Any

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import DeclarativeBase, Session


def find_by_id[T: DeclarativeBase](
    session: Session, model: type[T], id_: Any
) -> T | None:
    return session.get(model, id_)


def find_all[T: DeclarativeBase](
    session: Session,
    model: type[T],
    *,
    limit: int | None = None,
    offset: int = 0,
    **filters: Any,
) -> list[T]:
    """filters 는 열 이름 = 값 (같음 비교만). 순서는 기본 키 순이다."""
    statement = (
        select(model)
        .filter_by(**filters)
        # 순서를 고정하지 않으면 offset 으로 나눠 읽을 때 행이 겹치거나 빠진다.
        .order_by(*inspect(model).primary_key)
        .offset(offset)
    )
    if limit is not None:
        statement = statement.limit(limit)
    return list(session.scalars(statement))


def count[T: DeclarativeBase](session: Session, model: type[T], **filters: Any) -> int:
    statement = select(func.count()).select_from(model).filter_by(**filters)
    return session.scalar(statement) or 0


def create[T: DeclarativeBase](session: Session, model: type[T], **values: Any) -> T:
    """모르는 열 이름을 넘기면 모델 생성자가 오류를 낸다."""
    obj = model(**values)
    session.add(obj)
    session.flush()
    return obj


def update[T: DeclarativeBase](session: Session, obj: T, **values: Any) -> T:
    """모르는 열 이름은 오류다 — 그냥 두면 DB 에 없는 속성이 조용히 붙는다."""
    known = set(inspect(type(obj)).attrs.keys())
    unknown = set(values) - known
    if unknown:
        raise ValueError(f"{type(obj).__name__} 에 없는 속성: {sorted(unknown)}")
    for name, value in values.items():
        setattr(obj, name, value)
    session.flush()
    return obj


def delete(session: Session, obj: DeclarativeBase) -> None:
    session.delete(obj)
    session.flush()
