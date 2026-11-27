"""실제 PostgreSQL 에 붙는다. 먼저 `docker compose up -d --wait` 로 DB 를 띄운다."""

import pytest
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from agent_builder_infra import crud


class SampleBase(DeclarativeBase):
    """테스트 전용. 앱의 Base 에 섞지 않아야 Alembic 이 이 테이블을 보지 않는다."""


class Item(SampleBase):
    __tablename__ = "_test_crud_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    status: Mapped[str] = mapped_column(default="new")


class Clash(SampleBase):
    """열 이름이 crud 함수의 인자 이름(session·model·obj)과 같은 테이블."""

    __tablename__ = "_test_crud_clash"

    id: Mapped[int] = mapped_column(primary_key=True)
    session: Mapped[str]
    model: Mapped[str]
    obj: Mapped[str]


@pytest.fixture
def session(postgres_provider, db):
    """테스트마다 빈 테이블과 세션을 준다. 끝나면 테이블을 지운다."""
    engine = postgres_provider.engine
    SampleBase.metadata.drop_all(engine)
    SampleBase.metadata.create_all(engine)
    with db.session_scope() as session:
        yield session
    SampleBase.metadata.drop_all(engine)


def test_create_fills_id_and_default(session):
    item = crud.create(session, Item, name="a")

    assert item.id is not None
    assert item.status == "new"


def test_create_rejects_unknown_column(session):
    with pytest.raises(TypeError):
        crud.create(session, Item, name="a", colour="red")


def test_find_by_id(session):
    item = crud.create(session, Item, name="a")

    assert crud.find_by_id(session, Item, item.id) is item
    assert crud.find_by_id(session, Item, 999_999) is None


def test_find_all_filters_orders_and_pages(session):
    for name in ["a", "b", "c"]:
        crud.create(session, Item, name=name)
    crud.create(session, Item, name="d", status="done")

    assert [i.name for i in crud.find_all(session, Item)] == ["a", "b", "c", "d"]
    assert [i.name for i in crud.find_all(session, Item, status="new")] == [
        "a",
        "b",
        "c",
    ]
    assert [i.name for i in crud.find_all(session, Item, limit=2, offset=1)] == [
        "b",
        "c",
    ]


def test_count(session):
    crud.create(session, Item, name="a")
    crud.create(session, Item, name="b", status="done")

    assert crud.count(session, Item) == 2
    assert crud.count(session, Item, status="done") == 1


def test_update(session):
    item = crud.create(session, Item, name="a")

    crud.update(session, item, status="done")

    assert crud.count(session, Item, status="done") == 1


def test_update_rejects_unknown_column(session):
    item = crud.create(session, Item, name="a")

    with pytest.raises(ValueError, match="colour"):
        crud.update(session, item, colour="red")


def test_delete(session):
    item = crud.create(session, Item, name="a")

    crud.delete(session, item)

    assert crud.count(session, Item) == 0


def test_column_names_may_match_argument_names(session):
    row = crud.create(session, Clash, session="s", model="m", obj="o")

    assert crud.count(session, Clash, model="m") == 1
    assert crud.find_all(session, Clash, session="s")[0].id == row.id
    crud.update(session, row, obj="o2", model="m2")
    assert (row.model, row.obj) == ("m2", "o2")
