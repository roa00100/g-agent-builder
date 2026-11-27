from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, LargeBinary, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column

from agent_builder_infra.orm import Base


class ModelProviderRow(Base):
    """공급자 프로필 한 줄 — 어떻게 붙는가.

    model_alias.provider 가 이 name 을 가리킨다.
    """

    __tablename__ = "model_provider"
    __table_args__ = (
        CheckConstraint("timeout_seconds > 0", name="model_provider_timeout_positive"),
    )

    # 공급자 이름 (예: openrouter).
    name: Mapped[str] = mapped_column(Text, primary_key=True)
    # 공급자 API 주소.
    base_url: Mapped[str] = mapped_column(Text)
    # API 키의 암호문(Fernet). 평문은 두지 않는다. 아직 키를 넣지 않았으면 비어 있다.
    api_key_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    # 호출 한 번을 기다리는 기본 시간(초). 모델 대응표가 모델별로 덮어쓸 수 있다.
    timeout_seconds: Mapped[float] = mapped_column(Float)
    # 끄면 이 공급자로 보내지 않는다.
    enabled: Mapped[bool] = mapped_column(server_default=true())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
