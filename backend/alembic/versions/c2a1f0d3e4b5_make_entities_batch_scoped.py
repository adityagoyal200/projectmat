"""Make entities batch-scoped

Revision ID: c2a1f0d3e4b5
Revises: 777a5e0635c1
Create Date: 2026-07-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c2a1f0d3e4b5"
down_revision: str | Sequence[str] | None = "777a5e0635c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mentors",
        sa.Column("import_batch_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_mentors_import_batch_id_import_batches",
        "mentors",
        "import_batches",
        ["import_batch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE mentors m
        SET import_batch_id = p.import_batch_id
        FROM projects p
        WHERE p.mentor_id = m.id
          AND m.import_batch_id IS NULL
          AND p.import_batch_id IS NOT NULL
        """
    )

    op.drop_index("ix_mentors_email", table_name="mentors")
    op.create_index("ix_mentors_email", "mentors", ["email"], unique=False)
    op.create_unique_constraint(
        "uq_mentors_import_batch_email",
        "mentors",
        ["import_batch_id", "email"],
    )

    op.drop_index("ix_candidates_registration_number", table_name="candidates")
    op.create_index(
        "ix_candidates_registration_number",
        "candidates",
        ["registration_number"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_candidates_import_batch_registration_number",
        "candidates",
        ["import_batch_id", "registration_number"],
    )

    op.drop_constraint("projects_title_key", "projects", type_="unique")
    op.create_unique_constraint(
        "uq_projects_import_batch_title",
        "projects",
        ["import_batch_id", "title"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_projects_import_batch_title",
        "projects",
        type_="unique",
    )
    op.create_unique_constraint("projects_title_key", "projects", ["title"])

    op.drop_constraint(
        "uq_candidates_import_batch_registration_number",
        "candidates",
        type_="unique",
    )
    op.drop_index("ix_candidates_registration_number", table_name="candidates")
    op.create_index(
        "ix_candidates_registration_number",
        "candidates",
        ["registration_number"],
        unique=True,
    )

    op.drop_constraint(
        "uq_mentors_import_batch_email",
        "mentors",
        type_="unique",
    )
    op.drop_index("ix_mentors_email", table_name="mentors")
    op.create_index("ix_mentors_email", "mentors", ["email"], unique=True)

    op.drop_constraint(
        "fk_mentors_import_batch_id_import_batches",
        "mentors",
        type_="foreignkey",
    )
    op.drop_column("mentors", "import_batch_id")
