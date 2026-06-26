from sqlalchemy.ext.asyncio import AsyncSession

from app.features.imports.models import ImportBatch, ImportFile, ImportValidationIssue
from app.features.imports.parsers.workbook_parser import parse_workbook
from app.features.imports.schemas import ImportBatchResponse, SheetSummary


class WorkbookImportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def import_workbook(
        self, file_name: str, file_content: bytes
    ) -> ImportBatchResponse:
        """Parses the workbook, stages records, generates validation issues, and returns them synchronously."""

        # 1. Create ImportBatch (status 'parsing')
        batch = ImportBatch(status="parsing")
        self.db.add(batch)
        await self.db.flush()  # get batch.id

        # 2. Create ImportFile record
        import_file = ImportFile(
            import_batch_id=batch.id,
            file_name=file_name,
            file_type="workbook",
            status="uploaded",
        )
        self.db.add(import_file)
        await self.db.flush()

        # 3. Parse workbook
        parsed = parse_workbook(file_content)

        # 4. Save validation issues
        for issue in parsed.issues:
            db_issue = ImportValidationIssue(
                import_batch_id=batch.id,
                sheet_name=issue.sheet_name,
                row_number=issue.row_number,
                column_name=issue.column_name,
                issue_type=issue.severity,
                message=issue.message,
                # Optionally add raw_data_snapshot if needed, but not strictly required for phase 2 validation reporting.
            )
            self.db.add(db_issue)

        # 5. Determine final status
        has_errors = any(i.severity == "error" for i in parsed.issues)
        has_fatal = any(
            i.severity == "error" and i.message.startswith("Failed to open workbook")
            for i in parsed.issues
        )

        if has_fatal:
            batch.status = "failed"  # type: ignore
        else:
            batch.status = "validated"  # type: ignore

        await self.db.commit()
        await self.db.refresh(batch)

        # 6. Build synchronous response
        sheet_summaries = {}

        def _build_summary(sheet_name: str, rows_len: int) -> SheetSummary:
            errors = sum(
                1
                for i in parsed.issues
                if i.sheet_name == sheet_name and i.severity == "error"
            )
            warnings = sum(
                1
                for i in parsed.issues
                if i.sheet_name == sheet_name and i.severity == "warning"
            )
            return SheetSummary(total_rows=rows_len, errors=errors, warnings=warnings)

        sheet_summaries["Students Info"] = _build_summary(
            "Students Info", len(parsed.students)
        )
        sheet_summaries["Mentors info"] = _build_summary(
            "Mentors info", len(parsed.mentors)
        )
        sheet_summaries["Mentors-projects"] = _build_summary(
            "Mentors-projects", len(parsed.mentor_projects)
        )
        sheet_summaries["Probable projects"] = _build_summary(
            "Probable projects", len(parsed.probable_projects)
        )

        # Global errors (like missing sheets) that don't belong to a specific sheet row
        global_errors = sum(
            1 for i in parsed.issues if i.sheet_name is None and i.severity == "error"
        )
        if global_errors > 0:
            sheet_summaries["Global"] = SheetSummary(
                total_rows=0, errors=global_errors, warnings=0
            )

        return ImportBatchResponse(
            id=int(batch.id),  # type: ignore
            status=str(batch.status),  # type: ignore
            sheet_summaries=sheet_summaries,
            issues=parsed.issues,
        )
