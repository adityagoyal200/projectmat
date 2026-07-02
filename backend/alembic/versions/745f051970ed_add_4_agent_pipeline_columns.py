"""add_4_agent_pipeline_columns

Revision ID: 745f051970ed
Revises: f6e7d8c9b0a1
Create Date: 2026-06-30 12:24:47.732009

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "745f051970ed"
down_revision: str | Sequence[str] | None = "f6e7d8c9b0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "projects",
        sa.Column("problem_statement_link", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "projects", sa.Column("extracted_requirements", sa.JSON(), nullable=True)
    )
    op.add_column(
        "repository_evaluations",
        sa.Column("github_logic_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "repository_evaluations",
        sa.Column("ai_justification", sa.Text(), nullable=True),
    )
    op.add_column(
        "live_app_evaluations",
        sa.Column("screenshot_path", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("live_app_evaluations", "screenshot_path")
    op.drop_column("repository_evaluations", "ai_justification")
    op.drop_column("repository_evaluations", "github_logic_score")
    op.drop_column("projects", "extracted_requirements")
    op.drop_column("projects", "problem_statement_link")
