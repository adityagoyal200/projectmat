import asyncio
import re
from typing import ClassVar, Literal, cast

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.candidates.models import Candidate, CandidateDocument, CandidateSkill
from app.features.imports.models import ImportBatch, ImportFile, ImportValidationIssue
from app.features.imports.parsers.workbook_parser import parse_workbook
from app.features.imports.schemas import (
    ImportBatchResponse,
    ImportBatchSummary,
    SheetSummary,
)
from app.features.mentors.models import Mentor
from app.features.projects.models import Project, ProjectPreference, ProjectPrerequisite
from app.features.shared.models import Skill

logger = structlog.get_logger()


class ImportBatchNotFoundError(ValueError):
    """Raised when an import batch id does not exist."""


class WorkbookImportService:
    _background_tasks: ClassVar[set[asyncio.Task]] = set()

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_batch(self) -> ImportBatchSummary:
        """Create an empty import batch for subsequent file uploads."""
        batch = ImportBatch(status="created")
        self.db.add(batch)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(batch)

        return ImportBatchSummary(
            id=batch.id,
            status=cast(
                Literal["created", "parsing", "validated", "failed"],
                batch.status,
            ),
        )

    async def import_workbook(
        self, batch_id: int, file_name: str, file_content: bytes
    ) -> ImportBatchResponse:
        """Attach, parse, validate, and summarize a workbook for an import batch."""

        batch = await self.db.get(ImportBatch, batch_id)
        if batch is None:
            raise ImportBatchNotFoundError(f"Import batch {batch_id} was not found.")

        batch.status = "parsing"
        import_file = ImportFile(
            import_batch_id=batch.id,
            file_name=file_name,
            file_type="workbook",
            status="uploaded",
        )
        self.db.add(import_file)
        await self.db.flush()

        parsed = parse_workbook(file_content)

        for issue in parsed.issues:
            db_issue = ImportValidationIssue(
                import_batch_id=batch.id,
                sheet_name=issue.sheet_name,
                row_number=issue.row_number,
                column_name=issue.column_name,
                issue_code=issue.code,
                issue_type=issue.severity,
                message=issue.message,
            )
            self.db.add(db_issue)

        workbook_unreadable = any(i.blocking for i in parsed.issues)
        batch.status = "failed" if workbook_unreadable else "validated"
        can_proceed = not workbook_unreadable

        if can_proceed:
            # Save resumes_url if parsed
            if parsed.resumes_url:
                batch.resumes_url = parsed.resumes_url

            # 1. Save Mentors
            mentor_map = {}
            for _, mentor_row, _ in parsed.mentors:
                if not mentor_row.name:
                    continue
                email = (
                    mentor_row.email
                    or f"{mentor_row.name.replace(' ', '').lower()}@placeholder.com"
                )
                stmt = select(Mentor).where(Mentor.email == email)
                res = await self.db.execute(stmt)
                db_mentor = res.scalars().first()
                if not db_mentor:
                    db_mentor = Mentor(name=mentor_row.name, email=email)
                    self.db.add(db_mentor)
                    await self.db.flush()
                mentor_map[mentor_row.name] = db_mentor

            # 2. Save Projects & Prerequisites & Preferences
            for _, project_row, _ in parsed.mentor_projects:
                if not project_row.mentor_name or not project_row.title:
                    continue

                m_name = project_row.mentor_name
                db_mentor = mentor_map.get(m_name)
                if not db_mentor:
                    email = f"{m_name.replace(' ', '').lower()}@placeholder.com"
                    stmt = select(Mentor).where(Mentor.email == email)
                    res = await self.db.execute(stmt)
                    db_mentor = res.scalars().first()
                    if not db_mentor:
                        db_mentor = Mentor(name=m_name, email=email)
                        self.db.add(db_mentor)
                        await self.db.flush()
                    mentor_map[m_name] = db_mentor

                # Upsert by title; missing abstract/prerequisites stay null / unlinked.
                stmt = select(Project).where(Project.title == project_row.title)
                res = await self.db.execute(stmt)
                db_project = res.scalars().first()
                if not db_project:
                    db_project = Project(
                        import_batch_id=batch.id,
                        mentor_id=db_mentor.id,
                        title=project_row.title,
                        abstract=project_row.abstract or None,
                    )
                    self.db.add(db_project)
                    await self.db.flush()
                else:
                    db_project.import_batch_id = batch.id
                    db_project.mentor_id = db_mentor.id
                    db_project.abstract = project_row.abstract or None

                # Parse & link prerequisites only when provided
                if project_row.prerequisites:
                    skills_list = [
                        s.strip()
                        for s in project_row.prerequisites.split(",")
                        if s.strip()
                    ]
                    for skill_name in skills_list:
                        stmt = select(Skill).where(Skill.name.ilike(skill_name))
                        res = await self.db.execute(stmt)
                        db_skill = res.scalars().first()
                        if not db_skill:
                            db_skill = Skill(name=skill_name)
                            self.db.add(db_skill)
                            await self.db.flush()

                        stmt = select(ProjectPrerequisite).where(
                            ProjectPrerequisite.project_id == db_project.id,
                            ProjectPrerequisite.skill_id == db_skill.id,
                        )
                        res = await self.db.execute(stmt)
                        if not res.scalars().first():
                            pp = ProjectPrerequisite(
                                project_id=db_project.id,
                                skill_id=db_skill.id,
                                is_required="true",
                            )
                            self.db.add(pp)

                # Save preferences
                for pref_field, pref_type in [
                    (project_row.preference_1, "preference_1"),
                    (project_row.preference_2, "preference_2"),
                    (project_row.preference_3, "preference_3"),
                    (project_row.selected_students, "selected_students"),
                ]:
                    if pref_field:
                        values = [v.strip() for v in pref_field.split(",") if v.strip()]
                        for val in values:
                            stmt = select(ProjectPreference).where(
                                ProjectPreference.project_id == db_project.id,
                                ProjectPreference.preference_type == pref_type,
                                ProjectPreference.preference_value == val,
                            )
                            res = await self.db.execute(stmt)
                            if not res.scalars().first():
                                db_pref = ProjectPreference(
                                    project_id=db_project.id,
                                    preference_type=pref_type,
                                    preference_value=val,
                                )
                                self.db.add(db_pref)

            # 3. Save Candidates
            for _, student_row, _ in parsed.students:
                if not student_row.registration_number or not student_row.name:
                    continue

                stmt = select(Candidate).where(
                    Candidate.registration_number == student_row.registration_number
                )
                res = await self.db.execute(stmt)
                db_candidate = res.scalars().first()
                if not db_candidate:
                    db_candidate = Candidate(
                        import_batch_id=batch.id,
                        registration_number=student_row.registration_number,
                        name=student_row.name,
                        email=student_row.email,
                        phone=student_row.phone,
                    )
                    self.db.add(db_candidate)
                    await self.db.flush()
                else:
                    db_candidate.import_batch_id = batch.id
                    db_candidate.name = student_row.name
                    db_candidate.email = student_row.email
                    db_candidate.phone = student_row.phone

                if student_row.file:
                    stmt = select(CandidateDocument).where(
                        CandidateDocument.candidate_id == db_candidate.id,
                        CandidateDocument.document_type == "resume",
                    )
                    res = await self.db.execute(stmt)
                    db_doc = res.scalars().first()
                    if not db_doc:
                        db_doc = CandidateDocument(
                            candidate_id=db_candidate.id,
                            document_type="resume",
                            parse_status="pending",
                        )
                        self.db.add(db_doc)

            # Trigger background resume ingest task if URL exists
            if parsed.resumes_url:
                task = asyncio.create_task(
                    self.ingest_resumes_background_task(batch.id, parsed.resumes_url)
                )
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

        await self.db.commit()
        await self.db.refresh(batch)

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
            id=batch.id,
            status=cast(
                Literal["created", "parsing", "validated", "failed"],
                batch.status,
            ),
            can_proceed=can_proceed,
            sheet_summaries=sheet_summaries,
            issues=parsed.issues,
        )

    async def ingest_resumes_background_task(self, batch_id: int, resumes_url: str):
        """
        Background task to download and parse resumes from Google Drive in-memory.
        """
        from app.database import async_session
        from app.features.imports.drive_downloader import (
            download_resumes_from_drive,
            parse_pdf_bytes,
        )

        loop = asyncio.get_running_loop()
        resumes_data = await loop.run_in_executor(
            None, download_resumes_from_drive, resumes_url
        )

        if not resumes_data:
            logger.warn("No resumes found or downloaded from drive", batch_id=batch_id)
            return

        async with async_session() as db:
            for filename, file_bytes in resumes_data.items():
                match = re.search(
                    r"([A-Z]{3}\d{6}|[A-Z]{3}\d{5}|[A-Z]{3}\d{4})",
                    filename,
                    re.IGNORECASE,
                )
                if not match:
                    match = re.search(r"([A-Z]+\d+)", filename, re.IGNORECASE)

                if not match:
                    logger.warn(
                        "Could not extract registration number from resume filename",
                        filename=filename,
                    )
                    continue

                reg_num = match.group(1).upper()

                stmt = select(Candidate).where(Candidate.registration_number == reg_num)
                res = await db.execute(stmt)
                candidate = res.scalars().first()
                if not candidate:
                    logger.warn(
                        "Resume downloaded but candidate not found in database",
                        reg_num=reg_num,
                        filename=filename,
                    )
                    continue

                text = await loop.run_in_executor(None, parse_pdf_bytes, file_bytes)

                stmt = select(CandidateDocument).where(
                    CandidateDocument.candidate_id == candidate.id,
                    CandidateDocument.document_type == "resume",
                )
                res = await db.execute(stmt)
                db_doc = res.scalars().first()
                if not db_doc:
                    db_doc = CandidateDocument(
                        candidate_id=candidate.id,
                        document_type="resume",
                        parse_status="parsed",
                        parsed_text=text,
                    )
                    db.add(db_doc)
                else:
                    db_doc.parse_status = "parsed"
                    db_doc.parsed_text = text

                # Dynamic skill extraction (keywords matching)
                stmt = select(Skill)
                res = await db.execute(stmt)
                known_skills = res.scalars().all()

                keywords_to_check = {s.name: s for s in known_skills}
                common_keywords = [
                    "Python",
                    "PyTorch",
                    "TensorFlow",
                    "Machine Learning",
                    "Deep Learning",
                    "SQL",
                    "Java",
                    "C++",
                    "R ",
                    "React",
                    "Node.js",
                    "Docker",
                    "AWS",
                    "Git",
                ]
                for kw in common_keywords:
                    if kw not in keywords_to_check:
                        new_skill = Skill(name=kw)
                        db.add(new_skill)
                        await db.flush()
                        keywords_to_check[kw] = new_skill

                extracted_skills = []
                for skill_name, skill_obj in keywords_to_check.items():
                    pattern = rf"\b{re.escape(skill_name)}\b"
                    if re.search(pattern, text, re.IGNORECASE):
                        extracted_skills.append(skill_obj)

                for skill_obj in extracted_skills:
                    stmt = select(CandidateSkill).where(
                        CandidateSkill.candidate_id == candidate.id,
                        CandidateSkill.skill_id == skill_obj.id,
                    )
                    res = await db.execute(stmt)
                    if not res.scalars().first():
                        cs = CandidateSkill(
                            candidate_id=candidate.id,
                            skill_id=skill_obj.id,
                            source="resume",
                            confidence=1.0,
                        )
                        db.add(cs)

            await db.commit()
            logger.info(
                "Successfully ingested resumes in background for batch",
                batch_id=batch_id,
            )
