from agent_builder_infra import container
from agent_builder_infra.services import DbService, RedisService


def test_returns_one_instance_each():
    try:
        assert isinstance(container.get_db(), DbService)
        assert isinstance(container.get_redis(), RedisService)
        assert container.get_db() is container.get_db()
        assert container.get_redis() is container.get_redis()
    finally:
        container.close_all()


def test_close_all_then_rebuilds():
    first = container.get_db()
    assert first.fetch_value("select 1") == 1

    container.close_all()

    second = container.get_db()
    assert second is not first
    assert second.fetch_value("select 1") == 1
    container.close_all()
