from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Text, func, true
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from agent_builder_infra.orm import Base


class ModelAliasRow(Base):
    """모델 논리 이름의 대응표 한 줄. 논리 이름 → 공급자와 실제 모델 이름."""

    __tablename__ = "model_alias"
    __table_args__ = (
        # 받는 조각은 하나 이상이고, 셋(text·image·file) 밖의 말은 받지 않는다.
        # 이 셋은 모델 요청의 내용 조각 종류와 같다.
        CheckConstraint(
            "cardinality(input_kinds) > 0"
            " AND input_kinds <@ ARRAY['text', 'image', 'file']::text[]",
            name="model_alias_input_kinds_valid",
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
    # 끄면 이 이름으로 오는 요청을 거부한다. 지우지 않고 끌 수 있게 둔다.
    enabled: Mapped[bool] = mapped_column(server_default=true())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
