from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.features.mentors.models import Mentor
from app.features.mentors.schemas import MentorResponse

router = APIRouter(prefix="/api/mentors", tags=["Mentors"])


@router.get("", response_model=list[MentorResponse])
async def list_mentors(
    db: AsyncSession = Depends(get_db),
) -> list[Mentor]:
    """List all mentors, each including their linked project (if any)."""
    stmt = select(Mentor).options(selectinload(Mentor.project))
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
