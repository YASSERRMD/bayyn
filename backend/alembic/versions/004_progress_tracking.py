"""Add progress_pct and current_step to transcription_jobs

Revision ID: 004
Revises: 003
Create Date: 2025-06-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transcription_jobs",
        sa.Column(
            "progress_pct",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "transcription_jobs",
        sa.Column("current_step", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transcription_jobs", "current_step")
    op.drop_column("transcription_jobs", "progress_pct")
