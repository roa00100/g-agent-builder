"""명령줄을 실제로 돌린다. PostgreSQL·Redis 와 model_alias 테이블이 있어야 한다."""

import uuid

import pytest

from agent_builder_runtime.__main__ import main
from agent_builder_runtime.container import close_all, get_model_catalog


@pytest.fixture
def name():
    """테스트마다 새 이름을 쓰고, 끝나면 지운다."""
    name = f"test-{uuid.uuid4()}"
    yield name
    get_model_catalog().delete(name)
    close_all()


def test_set_show_disable_delete(name, capsys):
    command = ["model-catalog", "set", name, "--provider", "openrouter", "--model", "m"]
    assert main([*command, "--inputs", "text,file"]) == 0
    assert main(["model-catalog", "show", name]) == 0
    assert '"provider_model": "m"' in capsys.readouterr().out

    assert main(["model-catalog", "disable", name]) == 0
    assert "꺼짐" in capsys.readouterr().out

    assert main(["model-catalog", "delete", name]) == 0
    assert main(["model-catalog", "show", name]) == 1
    assert "대응표에 모델 이름" in capsys.readouterr().err


def test_rejects_bad_inputs(name):
    command = ["model-catalog", "set", name, "--provider", "p", "--model", "m"]

    assert main([*command, "--inputs", "video"]) == 2


def test_group_is_required(capsys):
    # 명령 없이 main 을 부르면 셸이 뜬다.
    # 한 번 하고 끝나는 실행에는 묶음이 꼭 있어야 한다.
    from agent_builder_runtime import cli

    with pytest.raises(SystemExit):
        cli.run([])
