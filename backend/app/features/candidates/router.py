from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.features.candidates.models import Candidate, CandidateSkill
from app.features.candidates.schemas import CandidateResponse

router = APIRouter(prefix="/api/candidates", tags=["Candidates"])


@router.get("", response_model=list[CandidateResponse])
async def list_candidates(
    import_batch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Candidate]:
    """Retrieve all candidates, optionally filtering by import batch."""
    stmt = select(Candidate).options(
        selectinload(Candidate.skills).selectinload(CandidateSkill.skill)
    )
    if import_batch_id is not None:
        stmt = stmt.where(Candidate.import_batch_id == import_batch_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


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
