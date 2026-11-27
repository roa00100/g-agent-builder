from datetime import datetime
from typing import get_args

from sqlalchemy import CheckConstraint, DateTime, Float, Text, func, true
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from agent_builder_core.contracts.model import InputKind
from agent_builder_infra.orm import Base

# 받는 조각 종류는 core 의 InputKind 한 곳에서 정의한다.
# 여기서는 그것으로 제약을 만든다.
# 종류를 바꾸면 이 제약이 달라지므로 새 마이그레이션도 같이 만든다.
_INPUT_KINDS_SQL = ", ".join(f"'{kind}'" for kind in get_args(InputKind))


class ModelAliasRow(Base):
    """모델 논리 이름의 대응표 한 줄. 논리 이름 → 공급자와 실제 모델 이름."""

    __tablename__ = "model_alias"
    __table_args__ = (
        # 받는 조각은 하나 이상이고, core 의 InputKind 밖의 말은 받지 않는다.
        CheckConstraint(
            "cardinality(input_kinds) > 0"
            f" AND input_kinds <@ ARRAY[{_INPUT_KINDS_SQL}]::text[]",
            name="model_alias_input_kinds_valid",
        ),
        CheckConstraint(
            "timeout_seconds IS NULL OR timeout_seconds > 0",
            name="model_alias_timeout_positive",
        ),
    )

    # 논리 이름 (예: fast, smart). 모델 요청의 model 에 적는 값이다.
    name: Mapped[str] = mapped_column(Text, primary_key=True)
    # 공급자 (예: openrouter).
    provider: Mapped[str] = mapped_column(Text)
    # 공급자 쪽 실제 모델 이름.
    provider_model: Mapped[str] = mapped_column(Text)
    # 이 모델이 받는 내용 조각 종류.
    input_kinds: Mapped[list[str]] = mapped_column(ARRAY(Text))
    # 이 모델만 다르게 기다릴 시간(초). 비우면 공급자 프로필의 기본값을 쓴다.
    timeout_seconds: Mapped[float | None] = mapped_column(Float)
    # 끄면 이 이름으로 오는 요청을 거부한다. 지우지 않고 끌 수 있게 둔다.
    enabled: Mapped[bool] = mapped_column(server_default=true())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
