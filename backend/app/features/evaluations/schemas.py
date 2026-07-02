from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvaluationFinding(BaseModel):
    severity: Literal["info", "warning", "error"]
    code: str
    message: str
    evidence: str | None = None


class RepositoryEvaluationRequest(BaseModel):
    repository_url: str = Field(max_length=1024)
    local_path: str | None = Field(
        default=None,
        description="Optional server-local checkout path foTruer deterministic inspection.",
    )
    clone_remote: bool = Field(
        default=True,
        description="Clone a remote Git repository into a temporary directory.",
    )
    run_tests: bool = Field(
        default=True,
        description="Run detected test commands after inspection.",
    )


class LiveAppEvaluationRequest(BaseModel):
    url: str = Field(max_length=1024)


class CandidateEvaluationRefreshRequest(BaseModel):
    fetch_remote_profiles: bool = Field(
        default=True,
        description="Fetch public profile metrics where API credentials allow it.",
    )
    evaluate_links: bool = Field(
        default=True,
        description="Evaluate extracted GitHub repository and live app links.",
    )
    clone_remote_repositories: bool = Field(
        default=True,
        description="Clone GitHub repositories before repository inspection.",
    )
    run_repository_tests: bool = Field(
        default=True,
        description="Run detected repository tests when a local checkout exists.",
    )
    wait_for_completion: bool = Field(
        default=True,
        description="Wait for the refresh to finish before responding.",
    )


class RepositoryEvaluationResponse(BaseModel):
    id: int | None = None
    candidate_id: int | None = None
    repository_url: str
    repository_name: str | None = None
    source: str = "resume"
    status: str
    score: float
    metrics: dict[str, Any]
    findings: list[EvaluationFinding]
    execution_log: str | None = None
    github_logic_score: float | None = None
    ai_justification: str | None = None
    evaluated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LiveAppEvaluationResponse(BaseModel):
    id: int | None = None
    candidate_id: int | None = None
    url: str
    source: str = "resume"
    status: str
    score: float
    http_status: int | None = None
    latency_ms: int | None = None
    metrics: dict[str, Any]
    findings: list[EvaluationFinding]
    agent_trace: list[dict[str, Any]]
    screenshot_path: str | None = None
    evaluated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CandidateProfileSummary(BaseModel):
    github_username: str | None = None
    github_repositories: list[str] = Field(default_factory=list)
    github_metrics: dict | None = None
    leetcode_username: str | None = None
    leetcode_metrics: dict | None = None
    codeforces_username: str | None = None
    codeforces_metrics: dict | None = None
    kaggle_username: str | None = None
    kaggle_metrics: dict | None = None
    scholar_id: str | None = None
    scholar_metrics: dict | None = None
    achievements: list[str] | None = None
    live_project_links: list[str] = Field(default_factory=list)


class CandidateEvaluationSummary(BaseModel):
    candidate_id: int
    candidate_name: str
    registration_number: str
    evaluation_status: str = "Pending"
    profile: CandidateProfileSummary
    repository_evaluations: list[RepositoryEvaluationResponse]
    live_app_evaluations: list[LiveAppEvaluationResponse]
    updated_at: datetime | None = None
    refresh_queued: bool = False


class AgentScoreSubmissionRequest(BaseModel):
    github_logic_score: float | None = Field(default=None, ge=0.0, le=1.0)
    live_feature_score: float | None = Field(default=None, ge=0.0, le=1.0)
    live_stability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    live_ui_ux_score: float | None = Field(default=None, ge=0.0, le=1.0)
    github_justification: str | None = Field(default=None, max_length=4000)
    live_justification: str | None = Field(default=None, max_length=4000)
    # End of file
