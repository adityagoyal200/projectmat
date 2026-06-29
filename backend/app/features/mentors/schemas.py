from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MentorProjectSummary(BaseModel):
    id: int
    title: str

    model_config = ConfigDict(from_attributes=True)


class MentorResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None
    project: MentorProjectSummary | None = None

    model_config = ConfigDict(from_attributes=True)
