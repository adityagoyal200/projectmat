from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    files = relationship(
        "ImportFile", back_populates="batch", cascade="all, delete-orphan"
    )
    validation_issues = relationship(
        "ImportValidationIssue", back_populates="batch", cascade="all, delete-orphan"
    )
    candidates = relationship("Candidate", back_populates="import_batch")


class ImportFile(Base):
    __tablename__ = "import_files"

    id = Column(Integer, primary_key=True, index=True)
    import_batch_id = Column(
        Integer, ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False
    )
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # e.g. workbook, resume
    file_path = Column(String(1024), nullable=True)  # path in local storage
    status = Column(String(50), nullable=False, default="uploaded")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    batch = relationship("ImportBatch", back_populates="files")


class ImportValidationIssue(Base):
    __tablename__ = "import_validation_issues"

    id = Column(Integer, primary_key=True, index=True)
    import_batch_id = Column(
        Integer, ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False
    )
    sheet_name = Column(String(255), nullable=True)
    row_number = Column(Integer, nullable=True)
    column_name = Column(String(255), nullable=True)
    issue_type = Column(String(50), nullable=False)  # error, warning
    message = Column(String(1024), nullable=False)
    raw_data_snapshot = Column(JSON, nullable=True)  # allowed for row snapshots
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    batch = relationship("ImportBatch", back_populates="validation_issues")
