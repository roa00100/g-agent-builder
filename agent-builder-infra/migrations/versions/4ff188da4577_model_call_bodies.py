"""model_call bodies

호출 기록에 본문 위치를 더한다 — 이름(request·sending·received·response) → 오브젝트
스토리지 키. 이미 있는 줄은 본문이 없던 때의 기록이라 빈 값('{}')이다.

Revision ID: 4ff188da4577
Revises: 0b3475285fc4
Create Date: 2026-11-28 12:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4ff188da4577"
down_revision: str | Sequence[str] | None = "0b3475285fc4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "model_call",
        sa.Column(
            "bodies",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("model_call", "bodies")
