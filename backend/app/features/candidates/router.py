from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.features.candidates.models import Candidate, CandidateSkill
from app.features.candidates.schemas import CandidateResponse
from app.features.imports.models import ImportBatch

router = APIRouter(prefix="/api/candidates", tags=["Candidates"])


@router.get("", response_model=list[CandidateResponse])
async def list_candidates(
    import_batch_id: int | None = None,
    all_batches: bool = Query(False, alias="all"),
    db: AsyncSession = Depends(get_db),
) -> list[CandidateResponse]:
    """Retrieve candidates.

    By default this returns only the latest import batch's candidates. Pass
    ``all=true`` to return candidates across every batch (needed to segregate
    and filter students by source), or ``import_batch_id`` to scope to one batch.
    """
    stmt = select(Candidate).options(
        selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
        selectinload(Candidate.import_batch).selectinload(ImportBatch.files),
    )
    if not all_batches:
        if import_batch_id is None:
            latest_res = await db.execute(select(func.max(ImportBatch.id)))
            import_batch_id = latest_res.scalar_one_or_none()
        if import_batch_id is not None:
            stmt = stmt.where(Candidate.import_batch_id == import_batch_id)

    result = await db.execute(stmt)
    candidates = result.scalars().all()

    response_list = []
    for c in candidates:
        source = "excel"
        if c.import_batch:
            has_workbook = any(f.file_type == "workbook" for f in c.import_batch.files)
            if not has_workbook and c.import_batch.resumes_url:
                source = "drive"

        data = CandidateResponse.model_validate(c)
        data.source = source
        response_list.append(data)

    return response_list


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
) -> Candidate:
    """Retrieve detailed candidate information by ID."""
    stmt = (
        select(Candidate)
        .options(selectinload(Candidate.skills).selectinload(CandidateSkill.skill))
        .where(Candidate.id == candidate_id)
    )

    result = await db.execute(stmt)
    candidate = result.scalars().first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return candidate
