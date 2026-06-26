from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    import_batch_id = Column(
        Integer, ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True
    )
    registration_number = Column(
        String(255), unique=True, index=True, nullable=False
    )  # Enforced uniqueness
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    import_batch = relationship("ImportBatch", back_populates="candidates")
    documents = relationship(
        "CandidateDocument", back_populates="candidate", cascade="all, delete-orphan"
    )
    skills = relationship(
        "CandidateSkill", back_populates="candidate", cascade="all, delete-orphan"
    )
    embeddings = relationship(
        "CandidateEmbedding", back_populates="candidate", cascade="all, delete-orphan"
    )


class CandidateDocument(Base):
    __tablename__ = "candidate_documents"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    import_file_id = Column(
        Integer, ForeignKey("import_files.id", ondelete="SET NULL"), nullable=True
    )
    document_type = Column(String(50), nullable=False, default="resume")
    parse_status = Column(String(50), nullable=False, default="pending")
    parsed_text = Column(String, nullable=True)  # Text extraction from resume

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("Candidate", back_populates="documents")
    import_file = relationship("ImportFile")


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    skill_id = Column(
        Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    source = Column(String(100), nullable=True)  # e.g., 'resume', 'workbook'
    confidence = Column(Float, nullable=True)

    candidate = relationship("Candidate", back_populates="skills")
    skill = relationship("Skill")


class CandidateEmbedding(Base):
    __tablename__ = "candidate_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    model_name = Column(String(255), nullable=False)
    model_version = Column(String(50), nullable=False)
    schema_version = Column(String(50), nullable=False)
    embedding = Column(
        Vector(1024), nullable=False
    )  # Using pgvector with example dimension 1024 for BGE-M3

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("Candidate", back_populates="embeddings")
