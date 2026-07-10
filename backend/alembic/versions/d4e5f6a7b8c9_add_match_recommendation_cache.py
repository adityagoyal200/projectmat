"""add match_recommendation_cache table

Revision ID: d4e5f6a7b8c9
Revises: c2a1f0d3e4b5
Create Date: 2026-07-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c2a1f0d3e4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create match_recommendation_cache table for cached LLM recommendations."""
    op.create_table(
        "match_recommendation_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("cache_type", sa.String(length=20), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("scoring_version", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["import_batches.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "batch_id", "cache_type", "entity_key", name="uq_match_rec_cache"
        ),
    )
    op.create_index(
        op.f("ix_match_recommendation_cache_id"),
        "match_recommendation_cache",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_match_recommendation_cache_batch_id",
        "match_recommendation_cache",
        ["batch_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop match_recommendation_cache table."""
    op.drop_index(
        "ix_match_recommendation_cache_batch_id",
        table_name="match_recommendation_cache",
    )
    op.drop_index(
        op.f("ix_match_recommendation_cache_id"),
        table_name="match_recommendation_cache",
    )
    op.drop_table("match_recommendation_cache")
