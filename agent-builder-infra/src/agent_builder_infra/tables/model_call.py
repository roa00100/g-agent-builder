from datetime import datetime
from decimal import Decimal
from typing import get_args

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from agent_builder_core.contracts.model import CallStatus, FailureKind, FinishReason
from agent_builder_infra.orm import Base


def _sql_list(literal_type) -> str:
    return ", ".join(f"'{value}'" for value in get_args(literal_type))


# 낱말 목록은 core 한 곳에서 정의하고, 여기서는 그것으로 제약을 만든다.
# 목록을 바꾸면 이 제약이 달라지므로 새 마이그레이션도 같이 만든다.
_STATUS_SQL = _sql_list(CallStatus)
_FINISH_SQL = _sql_list(FinishReason)
_FAILURE_SQL = _sql_list(FailureKind)


class ModelCallRow(Base):
    """모델 호출 기록 한 줄. 고치거나 지우지 않는다 — 있었던 일의 기록이라서."""

    __tablename__ = "model_call"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_SQL})", name="model_call_status_valid"),
        CheckConstraint(
            f"finish_reason IS NULL OR finish_reason IN ({_FINISH_SQL})",
            name="model_call_finish_reason_valid",
        ),
        CheckConstraint(
            f"failure_kind IS NULL OR failure_kind IN ({_FAILURE_SQL})",
            name="model_call_failure_kind_valid",
        ),
        # 성공이면 종료 사유·토큰이 있고 실패 종류가 없다. 실패면 그 반대.
        CheckConstraint(
            "(status = 'ok' AND finish_reason IS NOT NULL AND failure_kind IS NULL"
            " AND input_tokens IS NOT NULL AND output_tokens IS NOT NULL)"
            " OR (status = 'failed' AND failure_kind IS NOT NULL"
            " AND finish_reason IS NULL)",
            name="model_call_status_fields",
        ),
        CheckConstraint(
            "latency_ms >= 0 AND (cost IS NULL OR cost >= 0)"
            " AND (input_tokens IS NULL OR input_tokens >= 0)"
            " AND (output_tokens IS NULL OR output_tokens >= 0)",
            name="model_call_numbers_not_negative",
        ),
        # 최근 기록 보기(list)가 이 순서로 읽는다.
        Index("model_call_started_at", "started_at"),
        # 한 실행의 비용을 묶어 볼 때 쓴다(나중의 실행 상태와 잇는 열쇠).
        Index("model_call_run_id", "run_id"),
    )

    request_id: Mapped[str] = mapped_column(Text, primary_key=True)
    model: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    provider_model: Mapped[str] = mapped_column(Text)
    upstream_provider: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    finish_reason: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    # 정밀도를 정하지 않는다 — 공급자가 주는 자릿수(예: 0.00000285)를 그대로 둔다.
    cost: Mapped[Decimal | None] = mapped_column(Numeric)
    failure_kind: Mapped[str | None] = mapped_column(Text)
    failure_detail: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    run_id: Mapped[str | None] = mapped_column(Text)
    step_id: Mapped[str | None] = mapped_column(Text)
    attempt: Mapped[int | None] = mapped_column(Integer)
    # 남긴 본문의 위치 — 이름(request·sending·received·response) → 오브젝트 스토리지 키.
    # 본문 자체는 DB 에 두지 않는다 — 이미지·파일 조각까지 담기면 무거워서.
    bodies: Mapped[dict[str, str]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
