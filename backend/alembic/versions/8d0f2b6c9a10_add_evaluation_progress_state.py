"""add evaluation progress state

Revision ID: 8d0f2b6c9a10
Revises: 745f051970ed
Create Date: 2026-07-01 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d0f2b6c9a10"
down_revision: str | Sequence[str] | None = "745f051970ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add asynchronous evaluation progress fields."""
    op.add_column(
        "candidates",
        sa.Column(
            "evaluation_status",
            sa.String(length=50),
            server_default="Pending",
            nullable=False,
        ),
    )
    op.add_column(
        "import_batches",
        sa.Column("total_candidates", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "import_batches",
        sa.Column(
            "completed_candidates",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "import_batches",
        sa.Column(
            "cancellation_flag",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove asynchronous evaluation progress fields."""
    op.drop_column("import_batches", "cancellation_flag")
    op.drop_column("import_batches", "completed_candidates")
    op.drop_column("import_batches", "total_candidates")
    op.drop_column("candidates", "evaluation_status")
