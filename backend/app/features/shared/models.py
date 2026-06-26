from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Technology(Base):
    __tablename__ = "technologies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(255), nullable=False)
    entity_type = Column(String(255), nullable=False)
    entity_id = Column(Integer, nullable=False)
    metadata_json = Column(
        JSON, nullable=True
    )  # JSON allowed for unstructured audit metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
