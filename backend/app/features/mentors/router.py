from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.features.imports.models import ImportBatch
from app.features.mentors.models import Mentor
from app.features.mentors.schemas import MentorResponse

router = APIRouter(prefix="/api/mentors", tags=["Mentors"])


@router.get("", response_model=list[MentorResponse])
async def list_mentors(
    import_batch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Mentor]:
    """List all mentors, each including their linked project (if any)."""
    stmt = select(Mentor).options(selectinload(Mentor.project))
    if import_batch_id is None:
        latest_res = await db.execute(select(func.max(ImportBatch.id)))
        import_batch_id = latest_res.scalar_one_or_none()
    if import_batch_id is not None:
        stmt = stmt.where(Mentor.import_batch_id == import_batch_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{mentor_id}", response_model=MentorResponse)
async def get_mentor(
    mentor_id: int,
    db: AsyncSession = Depends(get_db),
) -> Mentor:
    """Retrieve a mentor by ID, including their linked project."""
    stmt = (
        select(Mentor)
        .options(selectinload(Mentor.project))
        .where(Mentor.id == mentor_id)
    )
    result = await db.execute(stmt)
    mentor = result.scalars().first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found.")
    return mentor
