from pydantic import BaseModel, ConfigDict


class SkillSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ProjectPrerequisiteSchema(BaseModel):
    skill: SkillSchema
    is_required: str | None = "true"

    model_config = ConfigDict(from_attributes=True)


class ProjectPreferenceSchema(BaseModel):
    preference_type: str
    preference_value: str

    model_config = ConfigDict(from_attributes=True)


class MentorSchema(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(BaseModel):
    id: int
    mentor_id: int
    title: str
    abstract: str | None = None
    mentor: MentorSchema | None = None
    prerequisites: list[ProjectPrerequisiteSchema] = []
    preferences: list[ProjectPreferenceSchema] = []

    model_config = ConfigDict(from_attributes=True)


class DummyProjectCreate(BaseModel):
    title: str
    abstract: str | None = None
    mentor_name: str
    mentor_email: str
    prerequisites: list[str] = []
