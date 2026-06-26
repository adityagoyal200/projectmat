"""add_column_name_to_import_validation_issues

Revision ID: b322f671e4b3
Revises: bbeb739cb3f2
Create Date: 2026-06-27 02:41:26.192059

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b322f671e4b3"
down_revision: str | Sequence[str] | None = "bbeb739cb3f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "import_validation_issues",
        sa.Column("column_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("import_validation_issues", "column_name")
