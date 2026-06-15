"""Add confidence metrics to transcript_documents

Revision ID: 002
Revises: 001
Create Date: 2025-06-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transcript_documents",
        sa.Column("average_confidence", sa.Numeric(5, 4), nullable=True),
    )
    op.add_column(
        "transcript_documents",
        sa.Column(
            "low_confidence_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("transcript_documents", "low_confidence_count")
    op.drop_column("transcript_documents", "average_confidence")
