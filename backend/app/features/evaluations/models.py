from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.features.candidates.models import Candidate


class RepositoryEvaluation(Base):
    """Static and optional execution review for a candidate repository."""

    __tablename__ = "repository_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    repository_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    repository_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="resume")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    execution_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_logic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    candidate: Mapped[Candidate] = relationship(back_populates="repository_evaluations")


class LiveAppEvaluation(Base):
    """Reachability and UI-health review for a candidate live application link."""

    __tablename__ = "live_app_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="resume")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    agent_trace: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    screenshot_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    candidate: Mapped[Candidate] = relationship(back_populates="live_app_evaluations")
