from pydantic import BaseModel, ConfigDict, Field


class ScoreComponents(BaseModel):
    embedding_similarity: float = Field(
        description="Blended embedding + LLM semantic fit (0.0-1.0)"
    )
    readiness: float = Field(description="LLM readiness to start (0.0-1.0)")
    growth_potential: float = Field(
        description="LLM growth/learnability score (0.0-1.0)"
    )
    interest: float = Field(description="LLM interest alignment (0.0-1.0)")
    prerequisite_overlap: float = Field(
        description="Tiered prerequisite overlap (0.0-1.0)"
    )
    resume_experience: float = Field(description="Resume experience depth (0.0-1.0)")
    preference_signal: float = Field(
        description="Workbook preference signal (informational only)"
    )
    preliminary_score: float = Field(
        description="Stage-1 deterministic score before LLM"
    )
    llm_evaluated: bool = Field(description="Whether full LLM evaluation was run")


class ScoreBreakdown(BaseModel):
    scoring_version: str
    formula: str
    weights: dict[str, float]
    weighted_contributions: dict[str, float]
    prerequisite_detail: str
    resume_experience_detail: str
    preference_detail: str
    embedding_detail: str
    llm_scoring_rationale: str
    llm_provider: str | None = None
    llm_model: str | None = None


class ProjectMatchRecommendation(BaseModel):
    rank: int
    project_id: int
    project_title: str
    mentor_name: str
    mentor_email: str | None = None
    mentor_phone: str | None = None
    final_score: float = Field(description="Weighted hybrid score (0.0-1.0)")
    score_components: ScoreComponents
    score_breakdown: ScoreBreakdown
    explanation: str
    technical_readiness: str
    growth_potential: str
    interest_alignment: str

    model_config = ConfigDict(from_attributes=True)


class StudentMatchRecommendation(BaseModel):
    rank: int
    candidate_id: int
    candidate_name: str
    registration_number: str
    final_score: float = Field(description="Weighted hybrid score (0.0-1.0)")
    score_components: ScoreComponents
    score_breakdown: ScoreBreakdown
    explanation: str
    technical_readiness: str
    growth_potential: str
    interest_alignment: str

    model_config = ConfigDict(from_attributes=True)


class StudentRecommendationsResponse(BaseModel):
    candidate_name: str
    registration_number: str
    recommendations: list[ProjectMatchRecommendation]


class ProjectRecommendationsResponse(BaseModel):
    project_id: int
    project_title: str
    recommendations: list[StudentMatchRecommendation]


class LlmPreviewRequest(BaseModel):
    prompt: str = Field(
        default="Say hello and confirm you can help match students to projects.",
        max_length=4000,
    )
    system_prompt: str = Field(
        default="You are an expert project matching assistant.",
        max_length=2000,
    )


class LlmPreviewResponse(BaseModel):
    provider: str
    model: str | None = None
    llm_enabled: bool
    configured: bool
    skipped: bool = False
    skip_reason: str | None = None
    error: str | None = None
    http_status: int | None = None
    prompt_preview: str | None = None
    raw_response: str
    response_length: int = 0


# ── Batch score matrix ────────────────────────────────────────────────────────


class BatchStudentSummary(BaseModel):
    candidate_id: int
    candidate_name: str
    registration_number: str


class BatchProjectSummary(BaseModel):
    project_id: int
    project_title: str
    mentor_name: str
    mentor_email: str | None = None


class PairScore(BaseModel):
    candidate_id: int
    project_id: int
    embedding_similarity: float = Field(
        description="Embedding / token similarity (0.0-1.0)"
    )
    prerequisite_overlap: float = Field(
        description="Tiered prerequisite overlap (0.0-1.0)"
    )
    resume_experience: float = Field(description="Resume experience depth (0.0-1.0)")
    preference_signal: float = Field(
        description="Workbook preference signal (informational)"
    )
    preliminary_score: float = Field(
        description="Composite deterministic score (0.0-1.0)"
    )


class BatchScoreMatrixResponse(BaseModel):
    batch_id: int
    students: list[BatchStudentSummary]
    projects: list[BatchProjectSummary]
    scores: list[PairScore]
    cached: bool = False
    computed_at: str | None = None
    note: str = (
        "Scores are deterministic (no LLM). "
        "Use /matching/student-recommendations or /matching/project-recommendations "
        "for full LLM-evaluated rankings."
    )
