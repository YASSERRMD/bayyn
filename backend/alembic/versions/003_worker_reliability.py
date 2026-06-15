"""Add retry_count and is_dead_letter to transcription_jobs

Revision ID: 003
Revises: 002
Create Date: 2025-06-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transcription_jobs",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "transcription_jobs",
        sa.Column(
            "is_dead_letter",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("transcription_jobs", "is_dead_letter")
    op.drop_column("transcription_jobs", "retry_count")
