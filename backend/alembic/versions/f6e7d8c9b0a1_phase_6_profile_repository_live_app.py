"""phase 6 profile repository live app evaluation

Revision ID: f6e7d8c9b0a1
Revises: a1b2c3d4e5f6
Create Date: 2026-06-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6e7d8c9b0a1"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Phase 6 profile and evaluation persistence."""
    op.add_column(
        "candidates", sa.Column("github_username", sa.String(255), nullable=True)
    )
    op.add_column(
        "candidates", sa.Column("github_metrics", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "candidates", sa.Column("leetcode_username", sa.String(255), nullable=True)
    )
    op.add_column(
        "candidates", sa.Column("leetcode_metrics", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "candidates", sa.Column("codeforces_username", sa.String(255), nullable=True)
    )
    op.add_column(
        "candidates", sa.Column("codeforces_metrics", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "candidates", sa.Column("kaggle_username", sa.String(255), nullable=True)
    )
    op.add_column(
        "candidates", sa.Column("kaggle_metrics", postgresql.JSONB(), nullable=True)
    )
    op.add_column("candidates", sa.Column("scholar_id", sa.String(255), nullable=True))
    op.add_column(
        "candidates", sa.Column("scholar_metrics", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "candidates", sa.Column("achievements", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "candidates",
        sa.Column("github_repositories", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "candidates", sa.Column("live_project_links", postgresql.JSONB(), nullable=True)
    )

    op.add_column(
        "batch_pair_scores",
        sa.Column("github_score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "batch_pair_scores",
        sa.Column(
            "coding_profiles_score", sa.Float(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "batch_pair_scores",
        sa.Column("achievements_score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "batch_pair_scores",
        sa.Column(
            "repository_quality_score", sa.Float(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "batch_pair_scores",
        sa.Column("live_app_score", sa.Float(), server_default="0", nullable=False),
    )

    op.create_table(
        "repository_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("repository_url", sa.String(1024), nullable=False),
        sa.Column("repository_name", sa.String(255), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("findings", postgresql.JSONB(), nullable=False),
        sa.Column("execution_log", sa.Text(), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_repository_evaluations_id"),
        "repository_evaluations",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_repository_evaluations_candidate_id",
        "repository_evaluations",
        ["candidate_id"],
        unique=False,
    )

    op.create_table(
        "live_app_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("findings", postgresql.JSONB(), nullable=False),
        sa.Column("agent_trace", postgresql.JSONB(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_live_app_evaluations_id"),
        "live_app_evaluations",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_live_app_evaluations_candidate_id",
        "live_app_evaluations",
        ["candidate_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Phase 6 profile and evaluation persistence."""
    op.drop_index(
        "ix_live_app_evaluations_candidate_id",
        table_name="live_app_evaluations",
    )
    op.drop_index(op.f("ix_live_app_evaluations_id"), table_name="live_app_evaluations")
    op.drop_table("live_app_evaluations")

    op.drop_index(
        "ix_repository_evaluations_candidate_id", table_name="repository_evaluations"
    )
    op.drop_index(
        op.f("ix_repository_evaluations_id"), table_name="repository_evaluations"
    )
    op.drop_table("repository_evaluations")

    op.drop_column("batch_pair_scores", "live_app_score")
    op.drop_column("batch_pair_scores", "repository_quality_score")
    op.drop_column("batch_pair_scores", "achievements_score")
    op.drop_column("batch_pair_scores", "coding_profiles_score")
    op.drop_column("batch_pair_scores", "github_score")

    op.drop_column("candidates", "live_project_links")
    op.drop_column("candidates", "github_repositories")
    op.drop_column("candidates", "achievements")
    op.drop_column("candidates", "scholar_metrics")
    op.drop_column("candidates", "scholar_id")
    op.drop_column("candidates", "kaggle_metrics")
    op.drop_column("candidates", "kaggle_username")
    op.drop_column("candidates", "codeforces_metrics")
    op.drop_column("candidates", "codeforces_username")
    op.drop_column("candidates", "leetcode_metrics")
    op.drop_column("candidates", "leetcode_username")
    op.drop_column("candidates", "github_metrics")
    op.drop_column("candidates", "github_username")
