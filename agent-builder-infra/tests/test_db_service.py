import pytest
from sqlalchemy.exc import MultipleResultsFound

TABLE = "_test_db_item"


@pytest.fixture
def table(db):
    """테스트마다 빈 테이블을 만들고 끝나면 지운다."""
    db.execute(f"drop table if exists {TABLE}")
    db.execute(f"create table {TABLE} (id serial primary key, name text not null)")
    yield TABLE
    db.execute(f"drop table {TABLE}")


def test_session_scope_commits(db, table):
    with db.session_scope() as session:
        db.execute(f"insert into {table} (name) values ('a')", session=session)

    assert db.fetch_value(f"select count(*) from {table}") == 1


def test_session_scope_rolls_back_on_error(db, table):
    with pytest.raises(RuntimeError):
        with db.session_scope() as session:
            db.execute(f"insert into {table} (name) values ('a')", session=session)
            raise RuntimeError

    assert db.fetch_value(f"select count(*) from {table}") == 0


def test_fetch_functions(db, table):
    assert db.execute(f"insert into {table} (name) values ('a'), ('b')") == 2

    rows = db.fetch_all(f"select name from {table} order by id")
    assert rows == [{"name": "a"}, {"name": "b"}]

    assert db.fetch_one(f"select name from {table} where name = :n", {"n": "b"}) == {
        "name": "b"
    }
    assert db.fetch_one(f"select name from {table} where name = 'z'") is None
    with pytest.raises(MultipleResultsFound):
        db.fetch_one(f"select name from {table}")


def test_cursor_commits_and_returns_dict_rows(db, table):
    with db.cursor() as cur:
        cur.execute(f"insert into {table} (name) values (%(n)s)", {"n": "a"})

    with db.cursor() as cur:
        cur.execute(f"select name from {table}")
        assert cur.fetchall() == [{"name": "a"}]


def test_cursor_rolls_back_on_error(db, table):
    with pytest.raises(RuntimeError):
        with db.cursor() as cur:
            cur.execute(f"insert into {table} (name) values ('a')")
            raise RuntimeError

    assert db.fetch_value(f"select count(*) from {table}") == 0
