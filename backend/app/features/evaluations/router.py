import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.dependencies import get_db
from app.features.evaluations.schemas import (
    AgentScoreSubmissionRequest,
    CandidateEvaluationRefreshRequest,
    CandidateEvaluationSummary,
    LiveAppEvaluationRequest,
    LiveAppEvaluationResponse,
    RepositoryEvaluationRequest,
    RepositoryEvaluationResponse,
)
from app.features.evaluations.service import EvaluationService

router = APIRouter(prefix="/api/evaluations", tags=["Evaluations"])

BACKGROUND_TASKS: set[asyncio.Task] = set()


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateEvaluationSummary,
)
async def get_candidate_evaluations(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
) -> CandidateEvaluationSummary:
    service = EvaluationService(db)
    try:
        return await service.get_candidate_summary(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/candidates/{candidate_id}/refresh",
    response_model=CandidateEvaluationSummary,
)
async def refresh_candidate_evaluations(
    candidate_id: int,
    request: CandidateEvaluationRefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> CandidateEvaluationSummary:
    request = request or CandidateEvaluationRefreshRequest()
    service = EvaluationService(db)

    async def run_refresh() -> CandidateEvaluationSummary:
        async with async_session() as session:
            background_service = EvaluationService(session)
            result = await background_service.refresh_candidate(
                candidate_id,
                fetch_remote_profiles=request.fetch_remote_profiles,
                evaluate_links=request.evaluate_links,
                clone_remote_repositories=request.clone_remote_repositories,
                run_repository_tests=request.run_repository_tests,
            )
            await session.commit()
            return result

    try:
        if request.wait_for_completion:
            return await run_refresh()
        summary = await service.get_candidate_summary(candidate_id)
        refresh_task = asyncio.create_task(run_refresh())
        BACKGROUND_TASKS.add(refresh_task)
        refresh_task.add_done_callback(BACKGROUND_TASKS.discard)
        return summary.model_copy(update={"refresh_queued": True})
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/candidates/{candidate_id}/repositories",
    response_model=RepositoryEvaluationResponse,
)
async def evaluate_candidate_repository(
    candidate_id: int,
    request: RepositoryEvaluationRequest,
    db: AsyncSession = Depends(get_db),
) -> RepositoryEvaluationResponse:
    service = EvaluationService(db)
    try:
        return await service.evaluate_repository_for_candidate(
            candidate_id,
            repository_url=request.repository_url,
            local_path=request.local_path,
            clone_remote=request.clone_remote,
            run_tests=request.run_tests,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/candidates/{candidate_id}/live-apps",
    response_model=LiveAppEvaluationResponse,
)
async def evaluate_candidate_live_app(
    candidate_id: int,
    request: LiveAppEvaluationRequest,
    db: AsyncSession = Depends(get_db),
) -> LiveAppEvaluationResponse:
    service = EvaluationService(db)
    try:
        return await service.evaluate_live_app_for_candidate(
            candidate_id, url=request.url
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/batches/{batch_id}/refresh",
    response_model=list[CandidateEvaluationSummary],
)
async def refresh_batch_evaluations(
    batch_id: int,
    request: CandidateEvaluationRefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[CandidateEvaluationSummary]:
    request = request or CandidateEvaluationRefreshRequest()
    service = EvaluationService(db)
    return await service.refresh_batch(
        batch_id,
        fetch_remote_profiles=request.fetch_remote_profiles,
        evaluate_links=request.evaluate_links,
        clone_remote_repositories=request.clone_remote_repositories,
        run_repository_tests=request.run_repository_tests,
    )


@router.post(
    "/candidates/{candidate_id}/agent-scores",
    response_model=CandidateEvaluationSummary,
)
async def submit_agent_scores(
    candidate_id: int,
    request: AgentScoreSubmissionRequest,
    db: AsyncSession = Depends(get_db),
) -> CandidateEvaluationSummary:
    service = EvaluationService(db)
    try:
        return await service.submit_agent_scores(candidate_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
