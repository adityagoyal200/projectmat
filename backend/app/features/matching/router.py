from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.features.matching.exceptions import (
    LlmEvaluationError,
    MatchingUnavailableError,
)
from app.features.matching.llm_client import generate_chat_completion
from app.features.matching.schemas import (
    BatchScoreMatrixResponse,
    LlmPreviewRequest,
    LlmPreviewResponse,
    ProjectRecommendationsResponse,
    StudentRecommendationsResponse,
)
from app.features.matching.service import MatchService

router = APIRouter(prefix="/api/matching", tags=["Matching"])


@router.post("/llm-preview", response_model=LlmPreviewResponse)
async def preview_llm(request: LlmPreviewRequest) -> LlmPreviewResponse:
    """
    Test the configured LLM provider without running full matching.
    Always attempts a real call (force=True) so you can inspect responses
    before enabling LLM_ENABLED.
    """
    result = await generate_chat_completion(
        request.prompt,
        request.system_prompt,
        force=True,
    )
    return LlmPreviewResponse(
        provider=result.provider,
        model=result.model,
        llm_enabled=settings.LLM_ENABLED,
        configured=settings.llm_is_configured(),
        skipped=result.skipped,
        skip_reason=result.skip_reason,
        error=result.error,
        http_status=result.http_status,
        prompt_preview=result.prompt_preview,
        raw_response=result.content,
        response_length=len(result.content),
    )


@router.get(
    "/student-recommendations/{registration_number}",
    response_model=StudentRecommendationsResponse,
)
async def get_student_recommendations(
    registration_number: str,
    db: AsyncSession = Depends(get_db),
) -> StudentRecommendationsResponse:
    """Retrieve ranked project recommendations for an existing candidate
    by registration number.
    """
    service = MatchService(db)
    try:
        return await service.recommend_projects_for_db_candidate(registration_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MatchingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LlmEvaluationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(exc),
                "raw_response": exc.raw_response,
            },
        ) from exc


@router.post(
    "/student-recommendations",
    response_model=StudentRecommendationsResponse,
)
async def recommend_projects_for_new_student(
    file: UploadFile = File(...),
    preferred_topics: str | None = Form(None),
    github_url: str | None = Form(None),
    leetcode_url: str | None = Form(None),
    codeforces_url: str | None = Form(None),
    kaggle_url: str | None = Form(None),
    scholar_url: str | None = Form(None),
    live_app_url: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> StudentRecommendationsResponse:
    """Upload a candidate's resume and get on-the-fly ranked project recommendations."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")

    resume_bytes = await file.read()
    topics = []
    if preferred_topics:
        topics = [t.strip() for t in preferred_topics.split(",") if t.strip()]

    service = MatchService(db)
    try:
        return await service.recommend_projects_for_student(
            resume_bytes=resume_bytes,
            preferred_topics=topics,
            github_url=github_url,
            leetcode_url=leetcode_url,
            codeforces_url=codeforces_url,
            kaggle_url=kaggle_url,
            scholar_url=scholar_url,
            live_app_url=live_app_url,
        )
    except MatchingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LlmEvaluationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(exc),
                "raw_response": exc.raw_response,
            },
        ) from exc


@router.get(
    "/project-recommendations/{project_id}",
    response_model=ProjectRecommendationsResponse,
)
async def get_project_recommendations(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> ProjectRecommendationsResponse:
    """Retrieve ranked recommended candidates for a project by project ID."""
    service = MatchService(db)
    try:
        return await service.recommend_candidates_for_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MatchingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LlmEvaluationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(exc),
                "raw_response": exc.raw_response,
            },
        ) from exc


@router.get(
    "/batch-scores/{batch_id}",
    response_model=BatchScoreMatrixResponse,
)
async def get_batch_score_matrix(
    batch_id: int,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
) -> BatchScoreMatrixResponse:
    """
    Return deterministic (no-LLM) scores for every student-project pair in a batch.

    Scores are computed once and cached in the database.
    Pass ?force=true to delete the cache and recompute from scratch.
    """
    service = MatchService(db)
    return await service.compute_batch_scores(batch_id, force=force)
