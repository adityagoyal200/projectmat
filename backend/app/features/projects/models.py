from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.features.mentors.models import Mentor
    from app.features.shared.models import Skill


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True
    )
    mentor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mentors.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    mentor: Mapped[Mentor] = relationship(back_populates="project")
    prerequisites: Mapped[list[ProjectPrerequisite]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    preferences: Mapped[list[ProjectPreference]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list[ProjectEmbedding]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectPrerequisite(Base):
    __tablename__ = "project_prerequisites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    is_required: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="true"
    )

    project: Mapped[Project] = relationship(back_populates="prerequisites")
    skill: Mapped[Skill] = relationship()


class ProjectPreference(Base):
    __tablename__ = "project_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    preference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    preference_value: Mapped[str] = mapped_column(String(255), nullable=False)

    project: Mapped[Project] = relationship(back_populates="preferences")


class ProjectEmbedding(Base):
    __tablename__ = "project_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="embeddings")
