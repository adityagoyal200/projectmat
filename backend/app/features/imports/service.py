import asyncio
import re
from typing import ClassVar, Literal, cast

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.candidates.models import Candidate, CandidateDocument, CandidateSkill
from app.features.imports.models import ImportBatch, ImportFile, ImportValidationIssue
from app.features.imports.parsers.workbook_parser import parse_workbook
from app.features.imports.profile_parser import extract_profiles
from app.features.imports.schemas import (
    ImportBatchCandidateItem,
    ImportBatchMentorItem,
    ImportBatchProjectItem,
    ImportBatchProjectMentorItem,
    ImportBatchResponse,
    ImportBatchSummary,
    ParsedWorkbook,
    SheetSummary,
    ValidationIssueOut,
)
from app.features.mentors.models import Mentor
from app.features.projects.models import Project, ProjectPreference, ProjectPrerequisite
from app.features.shared.models import Skill

logger = structlog.get_logger()


def _merge_unique_strings(existing: list[str] | None, incoming: list[str]) -> list[str]:
    merged = list(existing or [])
    seen = {value.strip().lower() for value in merged if value.strip()}
    for value in incoming:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(cleaned)
    return merged


class ImportBatchNotFoundError(ValueError):
    """Raised when an import batch id does not exist."""


class WorkbookImportService:
    _background_tasks: ClassVar[set[asyncio.Task]] = set()

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _build_batch_response(
        self,
        batch: ImportBatch,
        *,
        can_proceed: bool,
        parsed: ParsedWorkbook | None = None,
    ) -> ImportBatchResponse:
        issues_res = await self.db.execute(
            select(ImportValidationIssue).where(
                ImportValidationIssue.import_batch_id == batch.id
            )
        )
        db_issues = issues_res.scalars().all()

        if parsed is not None:

            def _build_summary(sheet_name: str, total_rows: int) -> SheetSummary:
                relevant = [i for i in parsed.issues if i.sheet_name == sheet_name]
                return SheetSummary(
                    total_rows=total_rows,
                    errors=sum(1 for i in relevant if i.severity == "error"),
                    warnings=sum(1 for i in relevant if i.severity == "warning"),
                )

            sheet_summaries = {
                "Students Info": _build_summary("Students Info", len(parsed.students)),
                "Mentors info": _build_summary("Mentors info", len(parsed.mentors)),
                "Mentors-projects": _build_summary(
                    "Mentors-projects", len(parsed.mentor_projects)
                ),
                "Probable projects": _build_summary(
                    "Probable projects", len(parsed.probable_projects)
                ),
            }
        else:
            sheet_summaries = {
                "Students Info": SheetSummary(total_rows=batch.total_candidates),
                "Mentors info": SheetSummary(),
                "Mentors-projects": SheetSummary(),
                "Probable projects": SheetSummary(),
            }

        candidates_res = await self.db.execute(
            select(Candidate)
            .where(Candidate.import_batch_id == batch.id)
            .order_by(Candidate.id.asc())
        )
        candidates = candidates_res.scalars().all()

        mentors_res = await self.db.execute(
            select(Mentor)
            .where(Mentor.import_batch_id == batch.id)
            .order_by(Mentor.id.asc())
        )
        mentors = mentors_res.scalars().all()

        projects_res = await self.db.execute(
            select(Project)
            .options(selectinload(Project.mentor))
            .where(Project.import_batch_id == batch.id)
            .order_by(Project.id.asc())
        )
        projects = projects_res.scalars().all()

        return ImportBatchResponse(
            id=batch.id,
            status=cast(
                Literal["created", "parsing", "validated", "failed"], batch.status
            ),
            can_proceed=can_proceed,
            sheet_summaries=sheet_summaries,
            issues=[
                ValidationIssueOut(
                    sheet_name=issue.sheet_name,
                    row_number=issue.row_number,
                    column_name=issue.column_name,
                    code=issue.issue_code,
                    severity=cast(Literal["error", "warning"], issue.issue_type),
                    message=issue.message,
                    blocking=False,
                )
                for issue in db_issues
            ],
            candidates=[
                ImportBatchCandidateItem.model_validate(candidate)
                for candidate in candidates
            ],
            mentors=[
                ImportBatchMentorItem.model_validate(mentor) for mentor in mentors
            ],
            projects=[
                ImportBatchProjectItem(
                    id=project.id,
                    mentor_id=project.mentor_id,
                    title=project.title,
                    abstract=project.abstract,
                    mentor=(
                        ImportBatchProjectMentorItem.model_validate(project.mentor)
                        if project.mentor
                        else None
                    ),
                )
                for project in projects
            ],
        )

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

    async def get_batch_details(self, batch_id: int) -> ImportBatchResponse:
        batch = await self.db.get(ImportBatch, batch_id)
        if batch is None:
            raise ImportBatchNotFoundError(f"Import batch {batch_id} was not found.")
        can_proceed = batch.status not in {"failed", "Failed", "Cancelled"}
        return await self._build_batch_response(batch, can_proceed=can_proceed)

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
        can_proceed = not workbook_unreadable
        batch.status = "failed" if not can_proceed else "validated"

        if can_proceed:
            if parsed.resumes_url:
                batch.resumes_url = parsed.resumes_url

            mentor_map = {}
            for _, mentor_row, _ in parsed.mentors:
                if not mentor_row.name:
                    continue
                email = (
                    mentor_row.email
                    or f"{mentor_row.name.replace(' ', '').lower()}@placeholder.com"
                )
                stmt = select(Mentor).where(
                    Mentor.import_batch_id == batch.id,
                    Mentor.email == email,
                )
                res = await self.db.execute(stmt)
                db_mentor = res.scalars().first()
                if not db_mentor:
                    db_mentor = Mentor(
                        import_batch_id=batch.id,
                        name=mentor_row.name,
                        email=email,
                    )
                    self.db.add(db_mentor)
                    await self.db.flush()
                else:
                    db_mentor.import_batch_id = batch.id
                    db_mentor.name = mentor_row.name
                mentor_map[mentor_row.name] = db_mentor

            for _, project_row, _ in parsed.mentor_projects:
                if not project_row.mentor_name or not project_row.title:
                    continue

                m_name = project_row.mentor_name
                db_mentor = mentor_map.get(m_name)
                if not db_mentor:
                    email = f"{m_name.replace(' ', '').lower()}@placeholder.com"
                    stmt = select(Mentor).where(
                        Mentor.import_batch_id == batch.id,
                        Mentor.email == email,
                    )
                    res = await self.db.execute(stmt)
                    db_mentor = res.scalars().first()
                    if not db_mentor:
                        db_mentor = Mentor(
                            import_batch_id=batch.id,
                            name=m_name,
                            email=email,
                        )
                        self.db.add(db_mentor)
                        await self.db.flush()
                    else:
                        db_mentor.import_batch_id = batch.id
                        db_mentor.name = m_name
                    mentor_map[m_name] = db_mentor

                stmt = select(Project).where(
                    Project.import_batch_id == batch.id,
                    Project.title == project_row.title,
                )
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

            for _, student_row, _ in parsed.students:
                if not student_row.registration_number or not student_row.name:
                    continue

                stmt = select(Candidate).where(
                    Candidate.import_batch_id == batch.id,
                    Candidate.registration_number == student_row.registration_number,
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
                        github_username=student_row.github_username,
                        leetcode_username=student_row.leetcode_username,
                        codeforces_username=student_row.codeforces_username,
                        kaggle_username=student_row.kaggle_username,
                        scholar_id=student_row.scholar_id,
                        live_project_links=[
                            link.strip()
                            for link in student_row.live_project_links.split(",")
                        ]
                        if student_row.live_project_links
                        else [],
                    )
                    self.db.add(db_candidate)
                    await self.db.flush()
                else:
                    db_candidate.import_batch_id = batch.id
                    db_candidate.name = student_row.name
                    db_candidate.email = student_row.email
                    db_candidate.phone = student_row.phone
                    if student_row.github_username:
                        db_candidate.github_username = student_row.github_username
                    if student_row.leetcode_username:
                        db_candidate.leetcode_username = student_row.leetcode_username
                    if student_row.codeforces_username:
                        db_candidate.codeforces_username = (
                            student_row.codeforces_username
                        )
                    if student_row.kaggle_username:
                        db_candidate.kaggle_username = student_row.kaggle_username
                    if student_row.scholar_id:
                        db_candidate.scholar_id = student_row.scholar_id
                    if student_row.live_project_links:
                        db_candidate.live_project_links = [
                            link.strip()
                            for link in student_row.live_project_links.split(",")
                        ]

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

            batch.total_candidates = len(
                [
                    student_row
                    for _, student_row, _ in parsed.students
                    if student_row.registration_number and student_row.name
                ]
            )
            batch.completed_candidates = batch.total_candidates

            if parsed.resumes_url:
                task = asyncio.create_task(
                    self.ingest_resumes_background_task(batch.id, parsed.resumes_url)
                )
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

        await self.db.commit()
        await self.db.refresh(batch)

        return await self._build_batch_response(
            batch,
            can_proceed=can_proceed,
            parsed=parsed,
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
                profiles = extract_profiles(text)

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

                candidate.github_username = (
                    candidate.github_username or profiles.github_username
                )
                candidate.leetcode_username = (
                    candidate.leetcode_username or profiles.leetcode_username
                )
                candidate.codeforces_username = (
                    candidate.codeforces_username or profiles.codeforces_username
                )
                candidate.kaggle_username = (
                    candidate.kaggle_username or profiles.kaggle_username
                )
                candidate.scholar_id = candidate.scholar_id or profiles.scholar_id
                candidate.github_repositories = _merge_unique_strings(
                    candidate.github_repositories,
                    profiles.github_repositories,
                )
                candidate.live_project_links = _merge_unique_strings(
                    candidate.live_project_links,
                    profiles.live_links,
                )
                if profiles.achievements:
                    existing_achievements = list(candidate.achievements or [])
                    candidate.achievements = _merge_unique_strings(
                        existing_achievements,
                        profiles.achievements,
                    )

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
