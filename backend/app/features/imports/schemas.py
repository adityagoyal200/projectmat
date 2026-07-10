from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StudentRow(BaseModel):
    name: str | None = None
    registration_number: str | None = None
    email: str | None = None
    phone: str | None = None
    file: str | None = None
    skills: str | None = None
    github_username: str | None = None
    leetcode_username: str | None = None
    codeforces_username: str | None = None
    kaggle_username: str | None = None
    scholar_id: str | None = None
    live_project_links: str | None = None

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
    code: str | None = None
    severity: Literal["error", "warning"]
    message: str
    blocking: bool = False


class SheetSummary(BaseModel):
    total_rows: int = 0
    errors: int = 0
    warnings: int = 0


ImportBatchStatus = Literal[
    "created",
    "parsing",
    "validated",
    "failed",
    "Pending",
    "Processing",
    "Completed",
    "Failed",
    "Cancelled",
]


class ImportBatchCandidateItem(BaseModel):
    id: int
    import_batch_id: int | None = None
    source: str | None = None
    registration_number: str
    name: str
    email: str | None = None
    phone: str | None = None
    github_username: str | None = None
    leetcode_username: str | None = None
    codeforces_username: str | None = None
    kaggle_username: str | None = None
    scholar_id: str | None = None
    live_project_links: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class ImportBatchMentorItem(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ImportBatchProjectMentorItem(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ImportBatchProjectItem(BaseModel):
    id: int
    mentor_id: int
    title: str
    abstract: str | None = None
    mentor: ImportBatchProjectMentorItem | None = None

    model_config = ConfigDict(from_attributes=True)


class ImportBatchResponse(BaseModel):
    id: int
    status: ImportBatchStatus
    can_proceed: bool = True
    sheet_summaries: dict[str, SheetSummary]
    issues: list[ValidationIssueOut]
    candidates: list[ImportBatchCandidateItem] = Field(default_factory=list)
    mentors: list[ImportBatchMentorItem] = Field(default_factory=list)
    projects: list[ImportBatchProjectItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ImportBatchSummary(BaseModel):
    id: int
    status: ImportBatchStatus
    total_candidates: int = 0
    completed_candidates: int = 0
    cancellation_flag: bool = False

    model_config = ConfigDict(from_attributes=True)


class ImportBatchListItem(BaseModel):
    id: int
    status: ImportBatchStatus
    created_at: str
    candidate_count: int = 0
    project_count: int = 0
    mentor_count: int = 0
    total_candidates: int = 0
    completed_candidates: int = 0
    cancellation_flag: bool = False

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
    resumes_url: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DriveResumesImportRequest(BaseModel):
    resumes_url: str
