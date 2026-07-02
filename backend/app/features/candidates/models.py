from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint(
            "import_batch_id",
            "registration_number",
            name="uq_candidates_import_batch_registration_number",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True
    )
    registration_number: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # --- Developer profile fields (Phase 6) ---
    github_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    leetcode_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    leetcode_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    codeforces_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    codeforces_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    kaggle_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kaggle_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scholar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scholar_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    achievements: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    github_repositories: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    live_project_links: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    evaluation_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Pending"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    import_batch: Mapped[ImportBatch | None] = relationship(back_populates="candidates")
    documents: Mapped[list[CandidateDocument]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    skills: Mapped[list[CandidateSkill]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list[CandidateEmbedding]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    repository_evaluations: Mapped[list[RepositoryEvaluation]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    live_app_evaluations: Mapped[list[LiveAppEvaluation]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class CandidateDocument(Base):
    __tablename__ = "candidate_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    import_file_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("import_files.id", ondelete="SET NULL"), nullable=True
    )
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="resume"
    )
    parse_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    parsed_text: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    candidate: Mapped[Candidate] = relationship(back_populates="documents")
    import_file: Mapped[ImportFile | None] = relationship()


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    candidate: Mapped[Candidate] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()


class CandidateEmbedding(Base):
    __tablename__ = "candidate_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    candidate: Mapped[Candidate] = relationship(back_populates="embeddings")


if TYPE_CHECKING:
    from app.features.evaluations.models import LiveAppEvaluation, RepositoryEvaluation
    from app.features.imports.models import ImportBatch, ImportFile
    from app.features.shared.models import Skill
