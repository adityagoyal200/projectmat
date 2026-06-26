from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    mentor_id = Column(
        Integer,
        ForeignKey("mentors.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )  # 1:1 relation as requested
    title = Column(String(512), nullable=False, unique=True)  # Unique title per project
    abstract = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    mentor = relationship("Mentor", back_populates="project")  # 1:1 relation
    prerequisites = relationship(
        "ProjectPrerequisite", back_populates="project", cascade="all, delete-orphan"
    )
    preferences = relationship(
        "ProjectPreference", back_populates="project", cascade="all, delete-orphan"
    )
    embeddings = relationship(
        "ProjectEmbedding", back_populates="project", cascade="all, delete-orphan"
    )


class ProjectPrerequisite(Base):
    __tablename__ = "project_prerequisites"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    skill_id = Column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    is_required = Column(
        String(50), nullable=True, default="true"
    )  # could be boolean or string

    project = relationship("Project", back_populates="prerequisites")
    skill = relationship("Skill")


class ProjectPreference(Base):
    __tablename__ = "project_preferences"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    preference_type = Column(
        String(50), nullable=False
    )  # e.g. 'student_selection', 'department'
    preference_value = Column(String(255), nullable=False)

    project = relationship("Project", back_populates="preferences")


class ProjectEmbedding(Base):
    __tablename__ = "project_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    model_name = Column(String(255), nullable=False)
    model_version = Column(String(50), nullable=False)
    schema_version = Column(String(50), nullable=False)
    embedding = Column(Vector(1024), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="embeddings")
