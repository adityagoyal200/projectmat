from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.features.projects.models import Project, ProjectPrerequisite
from app.features.projects.schemas import ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    import_batch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Project]:
    """Retrieve all projects, optionally filtering by import batch."""
    stmt = select(Project).options(
        selectinload(Project.mentor),
        selectinload(Project.prerequisites).selectinload(ProjectPrerequisite.skill),
        selectinload(Project.preferences),
    )
    if import_batch_id is not None:
        stmt = stmt.where(Project.import_batch_id == import_batch_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Retrieve detailed project information by ID."""
    stmt = (
        select(Project)
        .options(
            selectinload(Project.mentor),
            selectinload(Project.prerequisites).selectinload(ProjectPrerequisite.skill),
            selectinload(Project.preferences),
        )
        .where(Project.id == project_id)
    )

    result = await db.execute(stmt)
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project
