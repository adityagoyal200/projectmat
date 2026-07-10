from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.features.imports.models import ImportBatch
from app.features.mentors.models import Mentor
from app.features.projects.models import Project, ProjectPrerequisite
from app.features.projects.schemas import DummyProjectCreate, ProjectResponse
from app.features.shared.models import Skill

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    import_batch_id: int | None = None,
    dummy_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[Project]:
    """Retrieve all projects, optionally filtering by import batch or dummy status."""
    stmt = select(Project).options(
        selectinload(Project.mentor),
        selectinload(Project.prerequisites).selectinload(ProjectPrerequisite.skill),
        selectinload(Project.preferences),
    )
    if dummy_only:
        stmt = stmt.where(Project.import_batch_id.is_(None))
    else:
        if import_batch_id is None:
            latest_res = await db.execute(select(func.max(ImportBatch.id)))
            import_batch_id = latest_res.scalar_one_or_none()
        if import_batch_id is not None:
            stmt = stmt.where(Project.import_batch_id == import_batch_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/dummy", response_model=ProjectResponse, status_code=201)
async def create_dummy_project(
    request: DummyProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Create a dummy project for testing and batch-less drive candidates matching."""
    # Always create a fresh mentor for a dummy project. Projects.mentor_id is
    # unique (one project per mentor), so reusing an existing mentor — a prior
    # dummy mentor with the same email, or a workbook mentor who already owns a
    # project — would violate that constraint. Dummy mentors are batch-less
    # (import_batch_id is NULL), and Postgres treats NULLs as distinct in the
    # (import_batch_id, email) unique constraint, so duplicate emails are fine.
    mentor = Mentor(
        name=request.mentor_name,
        email=request.mentor_email,
        import_batch_id=None,
    )
    db.add(mentor)
    await db.flush()

    # Create dummy project
    project = Project(
        title=request.title,
        abstract=request.abstract,
        mentor_id=mentor.id,
        import_batch_id=None,
    )
    db.add(project)
    await db.flush()

    # Add prerequisites
    for skill_name in request.prerequisites:
        if not skill_name.strip():
            continue
        stmt_skill = select(Skill).where(Skill.name.ilike(skill_name.strip()))
        res_skill = await db.execute(stmt_skill)
        skill = res_skill.scalars().first()
        if not skill:
            skill = Skill(name=skill_name.strip())
            db.add(skill)
            await db.flush()

        prereq = ProjectPrerequisite(
            project_id=project.id, skill_id=skill.id, is_required="true"
        )
        db.add(prereq)

    await db.commit()
    await _invalidate_dummy_project_caches(db)

    # Reload project with loaded relations
    stmt_reload = (
        select(Project)
        .options(
            selectinload(Project.mentor),
            selectinload(Project.prerequisites).selectinload(ProjectPrerequisite.skill),
            selectinload(Project.preferences),
        )
        .where(Project.id == project.id)
    )
    res_reload = await db.execute(stmt_reload)
    return res_reload.scalars().one()


async def _invalidate_dummy_project_caches(db: AsyncSession) -> None:
    """Drop cached match results that score against dummy projects.

    Drive-link candidates are matched against dummy (batch-less) projects, and
    both the per-student recommendations and the batch score matrix are cached
    per batch. When a dummy project is added, edited, or removed those caches go
    stale, so clear them for every drive batch; the next request recomputes.
    """
    from app.features.imports.models import ImportBatch
    from app.features.matching.models import BatchPairScore, MatchRecommendationCache

    batches = (
        (await db.execute(select(ImportBatch).options(selectinload(ImportBatch.files))))
        .scalars()
        .all()
    )
    drive_ids = [
        b.id
        for b in batches
        if b.resumes_url and not any(f.file_type == "workbook" for f in b.files)
    ]
    if not drive_ids:
        return
    await db.execute(
        delete(MatchRecommendationCache).where(
            MatchRecommendationCache.batch_id.in_(drive_ids)
        )
    )
    await db.execute(
        delete(BatchPairScore).where(BatchPairScore.batch_id.in_(drive_ids))
    )
    await db.commit()


async def _set_project_prerequisites(
    db: AsyncSession, project_id: int, prerequisite_names: list[str]
) -> None:
    """Replace a project's prerequisites with the given skill names."""
    await db.execute(
        delete(ProjectPrerequisite).where(ProjectPrerequisite.project_id == project_id)
    )
    for skill_name in prerequisite_names:
        name = skill_name.strip()
        if not name:
            continue
        res_skill = await db.execute(select(Skill).where(Skill.name.ilike(name)))
        skill = res_skill.scalars().first()
        if not skill:
            skill = Skill(name=name)
            db.add(skill)
            await db.flush()
        db.add(
            ProjectPrerequisite(
                project_id=project_id, skill_id=skill.id, is_required="true"
            )
        )


@router.put("/dummy/{project_id}", response_model=ProjectResponse)
async def update_dummy_project(
    project_id: int,
    request: DummyProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Edit a dummy (batch-less) project's details, mentor, and prerequisites."""
    res = await db.execute(
        select(Project)
        .options(selectinload(Project.mentor))
        .where(Project.id == project_id)
    )
    project = res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.import_batch_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Only dummy (batch-less) projects can be edited here.",
        )

    project.title = request.title
    project.abstract = request.abstract
    if project.mentor:
        project.mentor.name = request.mentor_name
        project.mentor.email = request.mentor_email

    await _set_project_prerequisites(db, project.id, request.prerequisites)
    await db.commit()
    await _invalidate_dummy_project_caches(db)

    stmt_reload = (
        select(Project)
        .options(
            selectinload(Project.mentor),
            selectinload(Project.prerequisites).selectinload(ProjectPrerequisite.skill),
            selectinload(Project.preferences),
        )
        .where(Project.id == project.id)
    )
    res_reload = await db.execute(stmt_reload)
    return res_reload.scalars().one()


@router.delete("/dummy/{project_id}", status_code=204)
async def delete_dummy_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a dummy (batch-less) project and its mentor."""
    res = await db.execute(
        select(Project)
        .options(selectinload(Project.mentor))
        .where(Project.id == project_id)
    )
    project = res.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.import_batch_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Only dummy (batch-less) projects can be deleted here.",
        )
    mentor = project.mentor
    await db.delete(project)
    if mentor is not None:
        await db.delete(mentor)
    await db.commit()
    await _invalidate_dummy_project_caches(db)


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
