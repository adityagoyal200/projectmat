import asyncio
import re
import uuid
from pathlib import Path
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
from app.features.imports.skills_vocabulary import SKILLS_VOCABULARY
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


_REGISTRATION_NUMBER_RE = re.compile(r"([A-Z]{3}\d{4,6})", re.IGNORECASE)


async def _apply_resume_profiles_and_skills(
    db: AsyncSession, candidate: Candidate, text: str
) -> None:
    """Merge developer-profile handles and extract skills from resume text.

    Shared by the two resume ingestion paths: attaching resumes to workbook
    candidates, and creating candidates directly from a Drive folder. Assumes
    the caller has already stored/updated the candidate's resume document text.
    """
    profiles = extract_profiles(text)

    candidate.github_username = candidate.github_username or profiles.github_username
    candidate.leetcode_username = (
        candidate.leetcode_username or profiles.leetcode_username
    )
    candidate.codeforces_username = (
        candidate.codeforces_username or profiles.codeforces_username
    )
    candidate.kaggle_username = candidate.kaggle_username or profiles.kaggle_username
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
        candidate.achievements = _merge_unique_strings(
            list(candidate.achievements or []),
            profiles.achievements,
        )

    res = await db.execute(select(Skill))
    known_skills = res.scalars().all()
    skills_by_lower = {s.name.strip().lower(): s for s in known_skills}

    # Match against existing DB skills plus the curated vocabulary; only create
    # Skill rows for keywords actually present in the resume text.
    candidate_keywords = {s.name.strip() for s in known_skills}
    candidate_keywords.update(kw.strip() for kw in SKILLS_VOCABULARY)

    extracted_skills = []
    for skill_name in candidate_keywords:
        if not skill_name:
            continue
        pattern = rf"(?i)(?:^|[^\w]){re.escape(skill_name)}(?:[^\w]|$)"
        if not re.search(pattern, text):
            continue
        skill_obj = skills_by_lower.get(skill_name.lower())
        if not skill_obj:
            skill_obj = Skill(name=skill_name)
            db.add(skill_obj)
            await db.flush()
            skills_by_lower[skill_name.lower()] = skill_obj
        extracted_skills.append(skill_obj)

    for skill_obj in extracted_skills:
        stmt = select(CandidateSkill).where(
            CandidateSkill.candidate_id == candidate.id,
            CandidateSkill.skill_id == skill_obj.id,
        )
        res = await db.execute(stmt)
        if not res.scalars().first():
            db.add(
                CandidateSkill(
                    candidate_id=candidate.id,
                    skill_id=skill_obj.id,
                    source="resume",
                    confidence=1.0,
                )
            )


async def _extract_identity_from_resume(text: str, filename: str) -> tuple[str, str]:
    """Derive a candidate name and registration number from resume content.

    Registration number is matched by regex over the resume text. The name is
    read from the resume via the LLM when enabled, falling back to the first
    plausible line and finally to the filename stem. Returns
    ``(name, registration_number)``.
    """
    from app.features.matching.llm_client import generate_chat_completion

    reg_match = _REGISTRATION_NUMBER_RE.search(text)
    if reg_match:
        registration_number = reg_match.group(1).upper()
    else:
        import uuid

        registration_number = f"RES-{uuid.uuid4().hex[:12].upper()}"

    name: str | None = None
    snippet = text.strip()[:1500]
    if snippet:
        try:
            result = await generate_chat_completion(
                prompt=(
                    "The text below is the top of a resume. Reply with ONLY the "
                    "candidate's full name, nothing else. If no name is present, "
                    'reply with "UNKNOWN".\n\n'
                    f"{snippet}"
                ),
                system_prompt="You extract a person's full name from resume text.",
            )
            if not result.skipped and result.content:
                candidate_name = result.content.strip().splitlines()[0].strip()
                if (
                    candidate_name
                    and candidate_name.upper() != "UNKNOWN"
                    and len(candidate_name) <= 120
                ):
                    name = candidate_name
        except Exception as e:
            logger.warning("Resume name extraction via LLM failed", error=str(e))

    if not name:
        for line in text.splitlines():
            clean = line.strip()
            # A resume header name: a couple of words, mostly alphabetic.
            if (
                2 <= len(clean) <= 60
                and re.match(r"^[A-Za-z][A-Za-z.\-'\s]+$", clean)
                and 1 <= len(clean.split()) <= 5
            ):
                name = clean
                break

    if not name:
        stem = Path(filename).stem
        name = re.sub(r"[_\-]+", " ", stem).strip() or "Unknown Candidate"

    return name, registration_number


def _build_sheet_summary(
    parsed: ParsedWorkbook, sheet_name: str, total_rows: int
) -> SheetSummary:
    relevant = [i for i in parsed.issues if i.sheet_name == sheet_name]
    return SheetSummary(
        total_rows=total_rows,
        errors=sum(1 for i in relevant if i.severity == "error"),
        warnings=sum(1 for i in relevant if i.severity == "warning"),
    )


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

        files_stmt = select(ImportFile).where(ImportFile.import_batch_id == batch.id)
        files_res = await self.db.execute(files_stmt)
        batch_files = files_res.scalars().all()
        has_workbook = any(f.file_type == "workbook" for f in batch_files)
        source = "drive" if (not has_workbook and batch.resumes_url) else "excel"

        if parsed is not None:
            sheet_summaries = {
                "Students Info": _build_sheet_summary(
                    parsed, "Students Info", len(parsed.students)
                ),
                "Mentors info": _build_sheet_summary(
                    parsed, "Mentors info", len(parsed.mentors)
                ),
                "Mentors-projects": _build_sheet_summary(
                    parsed, "Mentors-projects", len(parsed.mentor_projects)
                ),
                "Probable projects": _build_sheet_summary(
                    parsed, "Probable projects", len(parsed.probable_projects)
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
                ImportBatchCandidateItem(
                    id=candidate.id,
                    import_batch_id=candidate.import_batch_id,
                    registration_number=candidate.registration_number,
                    name=candidate.name,
                    email=candidate.email,
                    phone=candidate.phone,
                    github_username=candidate.github_username,
                    leetcode_username=candidate.leetcode_username,
                    codeforces_username=candidate.codeforces_username,
                    kaggle_username=candidate.kaggle_username,
                    scholar_id=candidate.scholar_id,
                    live_project_links=candidate.live_project_links,
                    source=source,
                )
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

                # Import workbook-listed skills as CandidateSkill records
                if student_row.skills:
                    skill_names_from_wb = [
                        s.strip() for s in student_row.skills.split(",") if s.strip()
                    ]
                    for skill_name in skill_names_from_wb:
                        stmt = select(Skill).where(Skill.name.ilike(skill_name))
                        res = await self.db.execute(stmt)
                        db_skill = res.scalars().first()
                        if not db_skill:
                            db_skill = Skill(name=skill_name)
                            self.db.add(db_skill)
                            await self.db.flush()
                        stmt = select(CandidateSkill).where(
                            CandidateSkill.candidate_id == db_candidate.id,
                            CandidateSkill.skill_id == db_skill.id,
                        )
                        res = await self.db.execute(stmt)
                        if not res.scalars().first():
                            self.db.add(
                                CandidateSkill(
                                    candidate_id=db_candidate.id,
                                    skill_id=db_skill.id,
                                    source="workbook",
                                    confidence=1.0,
                                )
                            )

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

            # Re-importing into an existing batch changes its students/projects,
            # so any previously computed & cached match results or deterministic
            # pair scores for this batch are now stale. Drop them; the next
            # matching request recomputes and re-caches. (A brand-new upload is a
            # new batch id, so it never had cache to begin with.)
            from sqlalchemy import delete as sa_delete

            from app.features.matching.models import (
                BatchPairScore,
                MatchRecommendationCache,
            )

            await self.db.execute(
                sa_delete(MatchRecommendationCache).where(
                    MatchRecommendationCache.batch_id == batch.id
                )
            )
            await self.db.execute(
                sa_delete(BatchPairScore).where(BatchPairScore.batch_id == batch.id)
            )

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
            # Load this batch's candidates once for reg-number and name matching
            batch_cands_res = await db.execute(
                select(Candidate).where(Candidate.import_batch_id == batch_id)
            )
            batch_candidates = list(batch_cands_res.scalars().all())
            reg_to_candidate = {
                c.registration_number.upper(): c
                for c in batch_candidates
                if c.registration_number
            }

            def _match_candidate(filename: str) -> Candidate | None:
                # 1. Registration number in filename (scoped to this batch)
                match = re.search(
                    r"([A-Z]{3}\d{6}|[A-Z]{3}\d{5}|[A-Z]{3}\d{4})",
                    filename,
                    re.IGNORECASE,
                ) or re.search(r"([A-Z]+\d+)", filename, re.IGNORECASE)
                if match:
                    candidate = reg_to_candidate.get(match.group(1).upper())
                    if candidate:
                        return candidate

                # 2. Fallback: candidate name tokens in the filename
                fname_norm = re.sub(r"[^a-z0-9]", "", filename.lower())
                best: Candidate | None = None
                best_len = 0
                for c in batch_candidates:
                    if not c.name:
                        continue
                    tokens = [t for t in re.split(r"\s+", c.name.lower()) if len(t) > 2]
                    if tokens and all(
                        re.sub(r"[^a-z0-9]", "", t) in fname_norm for t in tokens
                    ):
                        name_len = sum(len(t) for t in tokens)
                        if name_len > best_len:
                            best, best_len = c, name_len
                return best

            for filename, file_bytes in resumes_data.items():
                candidate = _match_candidate(filename)
                if not candidate:
                    logger.warn(
                        "Could not match resume filename to any candidate in batch",
                        filename=filename,
                        batch_id=batch_id,
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

                await _apply_resume_profiles_and_skills(db, candidate, text)

            await db.commit()
            logger.info(
                "Successfully ingested resumes in background for batch",
                batch_id=batch_id,
            )

    async def import_drive_resumes(self, resumes_url: str) -> ImportBatchSummary:
        """Create a batch from a Drive folder of resumes (no workbook).

        Each resume becomes a Candidate whose identity is parsed from the PDF
        content. These drive-sourced candidates are matched only against dummy
        (batch-less) projects. The download/parse work runs in the background;
        poll ``GET /api/import-batches/{id}`` for progress.
        """
        batch = ImportBatch(status="parsing", resumes_url=resumes_url)
        self.db.add(batch)
        await self.db.flush()

        import_file = ImportFile(
            import_batch_id=batch.id,
            file_name=resumes_url,
            file_type="drive_resumes",
            status="uploaded",
        )
        self.db.add(import_file)
        await self.db.commit()
        await self.db.refresh(batch)

        task = asyncio.create_task(
            self.ingest_resume_folder_as_candidates(batch.id, resumes_url)
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        return ImportBatchSummary(
            id=batch.id,
            status=cast(
                Literal["created", "parsing", "validated", "failed"], batch.status
            ),
        )

    async def ingest_resume_folder_as_candidates(self, batch_id: int, resumes_url: str):
        """Download a Drive folder and create one Candidate per resume.

        Unlike :meth:`ingest_resumes_background_task`, which attaches resumes to
        candidates already present in the batch, this creates candidates from
        scratch — identity parsed from resume content — for a workbook-less
        import.
        """
        from app.database import async_session
        from app.features.imports.drive_downloader import (
            download_resumes_from_drive,
            parse_pdf_bytes,
        )

        loop = asyncio.get_running_loop()
        try:
            resumes_data = await loop.run_in_executor(
                None, download_resumes_from_drive, resumes_url
            )
        except Exception as e:
            logger.error(
                "Drive download failed for resume folder",
                batch_id=batch_id,
                error=str(e),
            )
            resumes_data = {}

        async with async_session() as db:
            batch = await db.get(ImportBatch, batch_id)
            if batch is None:
                logger.error(
                    "Batch vanished before resume ingestion", batch_id=batch_id
                )
                return

            if not resumes_data:
                logger.warn(
                    "No resumes found or downloaded from drive", batch_id=batch_id
                )
                batch.status = "failed"
                await db.commit()
                return

            # Publish the target count up front so the UI can show progress, and
            # commit each candidate as it is created. Incremental commits keep
            # partial progress durable if the task is interrupted (e.g. a dev
            # server reload) instead of losing the whole batch on rollback.
            batch.total_candidates = len(resumes_data)
            batch.completed_candidates = 0
            await db.commit()

            created = 0
            try:
                for filename, file_bytes in resumes_data.items():
                    try:
                        text = await loop.run_in_executor(
                            None, parse_pdf_bytes, file_bytes
                        )
                        if not text.strip():
                            logger.warn(
                                "Skipping resume with no extractable text",
                                filename=filename,
                                batch_id=batch_id,
                            )
                            continue

                        # Only the name is taken from the resume. Drive imports
                        # always get a synthetic RES- id: reg numbers scraped
                        # from resume text are unreliable and, when they look
                        # like roster ids (e.g. "MDS2025"), make Drive students
                        # indistinguishable from Excel students.
                        name, _ = await _extract_identity_from_resume(text, filename)
                        registration_number = f"RES-{uuid.uuid4().hex[:12].upper()}"

                        candidate = Candidate(
                            import_batch_id=batch_id,
                            registration_number=registration_number,
                            name=name,
                            evaluation_status="Pending",
                        )
                        candidate.documents.append(
                            CandidateDocument(
                                document_type="resume",
                                parse_status="parsed",
                                parsed_text=text,
                            )
                        )
                        db.add(candidate)
                        await db.flush()

                        await _apply_resume_profiles_and_skills(db, candidate, text)
                        created += 1
                        batch.completed_candidates = created
                        await db.commit()
                    except Exception as e:
                        # One bad resume must not abort the whole import.
                        await db.rollback()
                        logger.warning(
                            "Failed to ingest a resume; skipping",
                            filename=filename,
                            batch_id=batch_id,
                            error=str(e),
                        )
                        batch = await db.get(ImportBatch, batch_id)
                        if batch is None:
                            return

                batch.status = "validated" if created else "failed"
                await db.commit()
                logger.info(
                    "Created candidates from Drive resume folder",
                    batch_id=batch_id,
                    count=created,
                )
            except Exception as e:
                await db.rollback()
                logger.error(
                    "Drive resume ingestion failed",
                    batch_id=batch_id,
                    error=str(e),
                )
                batch = await db.get(ImportBatch, batch_id)
                if batch is not None:
                    batch.status = "validated" if created else "failed"
                    await db.commit()
