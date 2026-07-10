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
from sqlalchemy.dialects.postgresql import JSONB
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
    github_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    coding_profiles_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    achievements_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    repository_quality_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    live_app_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    preliminary_score: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MatchRecommendationCache(Base):
    """Persisted full (LLM-evaluated) recommendation responses.

    Recommendations are deterministic for a fixed batch (same students,
    projects, and scoring version), so once computed they are cached and served
    without re-running the LLM. One row per (batch, entity):

    * ``cache_type="student"`` — projects ranked for one student
      (``entity_key`` = registration number).
    * ``cache_type="project"`` — students ranked for one project / mentor
      (``entity_key`` = project id as string).

    Rows are keyed by ``import_batch_id`` and cascade-deleted with the batch, so
    a new upload (a new batch) never sees stale results; re-importing into an
    existing batch clears the batch's rows explicitly.
    """

    __tablename__ = "match_recommendation_cache"
    __table_args__ = (
        UniqueConstraint(
            "batch_id", "cache_type", "entity_key", name="uq_match_rec_cache"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cache_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
