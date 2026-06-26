from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StudentRow(BaseModel):
    name: str | None = None
    registration_number: str | None = None
    email: str | None = None
    phone: str | None = None
    file: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MentorRow(BaseModel):
    name: str | None = None
    email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MentorProjectRow(BaseModel):
    mentor_name: str | None = None
    mentor_profile: str | None = None
    title: str | None = None
    abstract: str | None = None
    prerequisites: str | None = None
    preference_1: str | None = None
    preference_2: str | None = None
    preference_3: str | None = None
    selected_students: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProbableProjectRow(BaseModel):
    idea: str | None = None
    author: str | None = None
    topic: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ValidationIssueOut(BaseModel):
    sheet_name: str | None = None
    row_number: int | None = None
    column_name: str | None = None
    severity: Literal["error", "warning"]
    message: str


class SheetSummary(BaseModel):
    total_rows: int = 0
    errors: int = 0
    warnings: int = 0


class ImportBatchResponse(BaseModel):
    id: int
    status: Literal["created", "parsing", "validated", "failed"]
    sheet_summaries: dict[str, SheetSummary]
    issues: list[ValidationIssueOut]

    model_config = ConfigDict(from_attributes=True)


class ParsedWorkbook(BaseModel):
    students: list[tuple[int, StudentRow, dict[str, str | None]]] = Field(
        default_factory=list
    )
    mentors: list[tuple[int, MentorRow, dict[str, str | None]]] = Field(
        default_factory=list
    )
    mentor_projects: list[tuple[int, MentorProjectRow, dict[str, str | None]]] = Field(
        default_factory=list
    )
    probable_projects: list[tuple[int, ProbableProjectRow, dict[str, str | None]]] = (
        Field(default_factory=list)
    )
    issues: list[ValidationIssueOut] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)
