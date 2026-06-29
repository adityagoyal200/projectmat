"""add batch_pair_scores table

Revision ID: a1b2c3d4e5f6
Revises: ddfc94f635f5
Create Date: 2026-06-29 09:18:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "ddfc94f635f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create batch_pair_scores table for cached deterministic match scores."""
    op.create_table(
        "batch_pair_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("embedding_similarity", sa.Float(), nullable=False),
        sa.Column("prerequisite_overlap", sa.Float(), nullable=False),
        sa.Column("resume_experience", sa.Float(), nullable=False),
        sa.Column("preference_signal", sa.Float(), nullable=False),
        sa.Column("preliminary_score", sa.Float(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["import_batches.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidates.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id", "candidate_id", "project_id", name="uq_batch_pair"
        ),
    )
    op.create_index(
        op.f("ix_batch_pair_scores_id"), "batch_pair_scores", ["id"], unique=False
    )
    op.create_index(
        "ix_batch_pair_scores_batch_id", "batch_pair_scores", ["batch_id"], unique=False
    )


def downgrade() -> None:
    """Drop batch_pair_scores table."""
    op.drop_index("ix_batch_pair_scores_batch_id", table_name="batch_pair_scores")
    op.drop_index(op.f("ix_batch_pair_scores_id"), table_name="batch_pair_scores")
    op.drop_table("batch_pair_scores")
