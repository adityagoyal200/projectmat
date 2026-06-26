from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.features.imports.schemas import ImportBatchResponse
from app.features.imports.service import WorkbookImportService

router = APIRouter(prefix="/api/imports", tags=["Imports"])


@router.post("/workbook", response_model=ImportBatchResponse, status_code=200)
async def upload_workbook(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and parse XLSX workbook.
    Synchronously returns the import batch details along with row-level validation issues.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=400, detail="Unsupported file type. Only .xlsx is allowed."
        )

    file_content = await file.read()

    service = WorkbookImportService(db)
    result = await service.import_workbook(file.filename, file_content)

    return result
