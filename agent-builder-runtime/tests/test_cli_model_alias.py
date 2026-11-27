"""명령줄을 실제로 돌린다. PostgreSQL·Redis 와 model_alias 테이블이 있어야 한다."""

import uuid

import pytest

from agent_builder_runtime.__main__ import main
from agent_builder_runtime.container import close_all, get_model_alias_service


@pytest.fixture
def name():
    """테스트마다 새 이름을 쓰고, 끝나면 지운다."""
    name = f"test-{uuid.uuid4()}"
    yield name
    get_model_alias_service().delete(name)
    close_all()


def test_set_show_disable_delete(name, capsys):
    command = ["model-alias", "set", name, "--provider", "openrouter", "--model", "m"]
    assert main([*command, "--inputs", "text,file"]) == 0
    assert main(["model-alias", "show", name]) == 0
    assert '"provider_model": "m"' in capsys.readouterr().out

    assert main(["model-alias", "disable", name]) == 0
    assert "꺼짐" in capsys.readouterr().out

    assert main(["model-alias", "delete", name]) == 0
    assert main(["model-alias", "show", name]) == 1
    assert "대응표에 없는" in capsys.readouterr().err


def test_rejects_bad_inputs(name):
    command = ["model-alias", "set", name, "--provider", "p", "--model", "m"]

    assert main([*command, "--inputs", "video"]) == 2


def test_group_is_required(capsys):
    with pytest.raises(SystemExit):
        main([])
