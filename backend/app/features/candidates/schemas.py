from pydantic import BaseModel, ConfigDict


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
    skills: list[CandidateSkillSchema] = []

    model_config = ConfigDict(from_attributes=True)
