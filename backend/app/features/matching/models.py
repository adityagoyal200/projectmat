from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class MatchRun(Base):
    __tablename__ = "match_runs"

    id = Column(Integer, primary_key=True, index=True)
    import_batch_id = Column(
        Integer, ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True
    )
    status = Column(String(50), nullable=False, default="queued")
    scoring_version = Column(String(50), nullable=True)
    embedding_model_version = Column(String(50), nullable=True)
    reranker_version = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    results = relationship(
        "MatchResult", back_populates="run", cascade="all, delete-orphan"
    )


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    match_run_id = Column(
        Integer, ForeignKey("match_runs.id", ondelete="CASCADE"), nullable=False
    )
    candidate_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    final_score = Column(Float, nullable=False)
    semantic_score = Column(Float, nullable=True)
    reranker_score = Column(Float, nullable=True)
    skill_score = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    run = relationship("MatchRun", back_populates="results")
    candidate = relationship("Candidate")
    project = relationship("Project")
    explanation = relationship(
        "MatchResultExplanation",
        back_populates="result",
        uselist=False,
        cascade="all, delete-orphan",
    )


class MatchResultExplanation(Base):
    __tablename__ = "match_result_explanations"

    id = Column(Integer, primary_key=True, index=True)
    match_result_id = Column(
        Integer,
        ForeignKey("match_results.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    explanation_text = Column(Text, nullable=False)
    is_fallback = Column(String(10), default="false")  # "true" or "false"

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    result = relationship("MatchResult", back_populates="explanation")
