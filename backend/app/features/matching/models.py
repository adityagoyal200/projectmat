from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.features.candidates.models import Candidate
    from app.features.projects.models import Project


class MatchRun(Base):
    __tablename__ = "match_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    scoring_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding_model_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    reranker_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    results: Mapped[list[MatchResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("match_runs.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reranker_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    skill_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped[MatchRun] = relationship(back_populates="results")
    candidate: Mapped[Candidate] = relationship()
    project: Mapped[Project] = relationship()
    explanation: Mapped[MatchResultExplanation | None] = relationship(
        back_populates="result",
        uselist=False,
        cascade="all, delete-orphan",
    )


class MatchResultExplanation(Base):
    __tablename__ = "match_result_explanations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_result_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("match_results.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    explanation_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_fallback: Mapped[str] = mapped_column(String(10), default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    result: Mapped[MatchResult] = relationship(back_populates="explanation")


class BatchPairScore(Base):
    """Persisted deterministic (no-LLM) scores for a student-project pair in a batch."""

    __tablename__ = "batch_pair_scores"
    __table_args__ = (
        UniqueConstraint(
            "batch_id", "candidate_id", "project_id", name="uq_batch_pair"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    embedding_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    prerequisite_overlap: Mapped[float] = mapped_column(Float, nullable=False)
    resume_experience: Mapped[float] = mapped_column(Float, nullable=False)
    preference_signal: Mapped[float] = mapped_column(Float, nullable=False)
    preliminary_score: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
