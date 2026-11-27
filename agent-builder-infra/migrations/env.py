from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from agent_builder_infra.orm import Base
from agent_builder_infra.settings import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 접속 주소는 alembic.ini 가 아니라 설정 모듈에서 읽는다.
# 비밀번호를 커밋하지 않기 위해서다.
DATABASE_URL = get_settings().database_url

# 테이블 모델은 Base 를 상속한다. 모델 모듈이 생기면 여기서 import 해야
# autogenerate 가 그 테이블을 본다.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """DB 에 붙지 않고 SQL 만 출력한다 (`alembic upgrade head --sql`)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """DB 에 붙어서 마이그레이션을 적용한다."""
    # 명령 한 번에 연결 하나만 쓰므로 풀을 두지 않는다.
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
