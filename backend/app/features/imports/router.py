from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.features.candidates.models import Candidate
from app.features.imports.models import ImportBatch
from app.features.imports.schemas import (
    DriveResumesImportRequest,
    ImportBatchListItem,
    ImportBatchResponse,
    ImportBatchSummary,
)
from app.features.imports.service import ImportBatchNotFoundError, WorkbookImportService
from app.features.imports.template import build_workbook_template
from app.features.mentors.models import Mentor
from app.features.projects.models import Project

router = APIRouter(prefix="/api/import-batches", tags=["Import Batches"])


@router.get("", response_model=list[ImportBatchListItem])
async def list_import_batches(
    db: AsyncSession = Depends(get_db),
) -> list[ImportBatchListItem]:
    """List all import batches with candidate and project counts."""
    batches_res = await db.execute(select(ImportBatch).order_by(ImportBatch.id.desc()))
    batches = batches_res.scalars().all()

    # Count candidates and projects per batch in two separate queries
    cand_counts_res = await db.execute(
        select(
            Candidate.import_batch_id, func.count(Candidate.id).label("cnt")
        ).group_by(Candidate.import_batch_id)
    )
    cand_counts = {row.import_batch_id: row.cnt for row in cand_counts_res}

    proj_counts_res = await db.execute(
        select(Project.import_batch_id, func.count(Project.id).label("cnt")).group_by(
            Project.import_batch_id
        )
    )
    proj_counts = {row.import_batch_id: row.cnt for row in proj_counts_res}

    mentor_counts_res = await db.execute(
        select(Mentor.import_batch_id, func.count(Mentor.id).label("cnt")).group_by(
            Mentor.import_batch_id
        )
    )
    mentor_counts = {row.import_batch_id: row.cnt for row in mentor_counts_res}

    return [
        ImportBatchListItem(
            id=b.id,
            status=b.status,  # type: ignore[arg-type]
            created_at=b.created_at.isoformat(),
            candidate_count=cand_counts.get(b.id, 0),
            project_count=proj_counts.get(b.id, 0),
            mentor_count=mentor_counts.get(b.id, 0),
            total_candidates=b.total_candidates,
            completed_candidates=b.completed_candidates,
            cancellation_flag=b.cancellation_flag,
        )
        for b in batches
    ]


@router.post("", response_model=ImportBatchSummary, status_code=201)
async def create_import_batch(
    db: AsyncSession = Depends(get_db),
) -> ImportBatchSummary:
    """Create an empty import batch for workbook and resume files."""
    service = WorkbookImportService(db)
    return await service.create_batch()


XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# Declared ahead of /{batch_id} so "template" is not parsed as a batch id.
@router.get("/template")
async def download_workbook_template() -> Response:
    """Download the blank workbook to fill in and upload."""
    return Response(
        content=build_workbook_template(),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="import-template.xlsx"'},
    )


@router.get("/{batch_id}", response_model=ImportBatchResponse)
async def get_import_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
) -> ImportBatchResponse:
    service = WorkbookImportService(db)
    try:
        return await service.get_batch_details(batch_id)
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{batch_id}/files", response_model=ImportBatchResponse, status_code=200)
async def attach_workbook_file(
    batch_id: int,
    file: UploadFile = File(...),
    file_type: str = Form("workbook"),
    db: AsyncSession = Depends(get_db),
) -> ImportBatchResponse:
    """Attach and parse a workbook for an import batch."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    if file_type != "workbook":
        raise HTTPException(
            status_code=400,
            detail="Only workbook uploads are supported in this phase.",
        )
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only .xlsx is allowed.",
        )

    file_content = await file.read()
    service = WorkbookImportService(db)

    try:
        return await service.import_workbook(batch_id, file.filename, file_content)
    except ImportBatchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/drive-resumes", response_model=ImportBatchSummary, status_code=201)
async def import_drive_resumes(
    request: DriveResumesImportRequest,
    db: AsyncSession = Depends(get_db),
) -> ImportBatchSummary:
    """Create a batch and import resumes directly from a Drive link (no workbook)."""
    service = WorkbookImportService(db)
    return await service.import_drive_resumes(request.resumes_url)
