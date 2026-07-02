from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.features.candidates.models import Candidate


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    resumes_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    total_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_candidates: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    cancellation_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    files: Mapped[list[ImportFile]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )
    validation_issues: Mapped[list[ImportValidationIssue]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )
    candidates: Mapped[list[Candidate]] = relationship(back_populates="import_batch")


class ImportFile(Base):
    __tablename__ = "import_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_batch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    batch: Mapped[ImportBatch] = relationship(back_populates="files")


class ImportValidationIssue(Base):
    __tablename__ = "import_validation_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_batch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False
    )
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issue_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    raw_data_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    batch: Mapped[ImportBatch] = relationship(back_populates="validation_issues")


if TYPE_CHECKING:
    from app.features.candidates.models import Candidate
