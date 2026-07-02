from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class CandidateSkillSchema(BaseModel):
    skill: SkillSchema
    source: str | None = None
    confidence: float | None = None

    model_config = ConfigDict(from_attributes=True)


class CandidateResponse(BaseModel):
    id: int
    import_batch_id: int | None = None
    registration_number: str
    name: str
    email: str | None = None
    phone: str | None = None
    evaluation_status: str = "Pending"
    github_username: str | None = None
    github_metrics: dict | None = None
    github_repositories: list[str] | None = None
    leetcode_username: str | None = None
    leetcode_metrics: dict | None = None
    codeforces_username: str | None = None
    codeforces_metrics: dict | None = None
    kaggle_username: str | None = None
    kaggle_metrics: dict | None = None
    scholar_id: str | None = None
    scholar_metrics: dict | None = None
    achievements: list[str] | None = None
    live_project_links: list[str] | None = None
    skills: list[CandidateSkillSchema] = Field(default_factory=list)

    @field_validator("achievements", "live_project_links", mode="before")
    @classmethod
    def validate_list_fields(cls, v: Any) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, dict) and "items" in v and isinstance(v["items"], list):
            return v["items"]
        if isinstance(v, str):
            return [v]
        return []

    model_config = ConfigDict(from_attributes=True)
