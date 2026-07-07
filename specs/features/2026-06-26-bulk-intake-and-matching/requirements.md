# Feature Specification: Bulk Intake and Matching

## Feature Name

Bulk Intake and Matching

## Status

`[x] Approved`

## Author

ProjectMatchAI Engineering Team

## Date

2026-06-26

## Related Phase

Phases 1-10 - Standalone Upload-and-Review MVP

## Related ADR

`specs/adrs/ADR-0001-standalone-bulk-intake-matching-mvp.md`

---

## 1. Problem Statement

ProjectMatchAI is now a standalone upload-and-review app for the MVP. A program operator provides candidate/student data through spreadsheets and optional resume files, plus mentor/project data through workbooks like the provided alumni mentorship workbook.

The problem is not just "read Excel." The system must safely handle messy real-world data, validate it, normalize it into canonical records, run explainable AI matching, and return auditable results for human review.

If this is not solved correctly, recommendations will be hard to trust, impossible to reproduce, and difficult to evolve into a future integration.

---

## 2. Proposed Solution

Build a bulk intake and matching workflow:

1. Create an import batch.
2. Parse one or more workbook files.
3. Validate sheets, headers, rows, and resume references.
4. Normalize candidate, mentor, project, prerequisite, and preference data into canonical tables.
5. Parse resumes when available and enrich candidate profiles.
6. Generate versioned embeddings for candidates and projects.
7. Run explicit match jobs against selected import batches.
8. Rank candidates per project with component score breakdowns.
9. Generate source-grounded explanations through `ai/generation/`.
10. Return or export persisted results for review.

This feature produces an approved architecture and specification first. Production implementation starts only after approval.

---

## 3. User Stories

- As a program operator, I want to import a student workbook and a mentor/project workbook so that I do not manually re-enter program data.
- As a program operator, I want row-level validation errors and warnings so that I can fix bad data before trusting the match results.
- As a future integration consumer, I want a backend API boundary so that the core pipeline can later plug into a larger system without moving parsing or matching into the frontend.
- As a reviewer, I want ranked candidates for every project with score components and explanations so that I can make informed final decisions.
- As a technical operator, I want every match run tied to input versions and model versions so that recommendations can be audited and reproduced.

---

## 4. Input Contract

### Reference Workbook Shape

The provided workbook contains four relevant sheets:

| Sheet               | Required for MVP | Purpose                                                                                  |
| ------------------- | ---------------- | ---------------------------------------------------------------------------------------- |
| `Students Info`     | Yes              | Candidate identity and resume references.                                                |
| `Mentors info`      | Yes              | Mentor contact records.                                                                  |
| `Mentors-projects`  | Yes              | Project records, mentor profiles, prerequisites, preferences, and historical selections. |
| `Probable projects` | No               | Optional project idea backlog.                                                           |

### `Students Info`

| Source Column         | Canonical Meaning          | Required | Validation                                        |
| --------------------- | -------------------------- | -------- | ------------------------------------------------- |
| `Name`                | Candidate full name        | Yes      | Non-empty.                                        |
| `Registration Number` | External candidate id      | Yes      | Unique within import batch.                       |
| `Email`               | Candidate email            | No       | Valid email if present; `N/A` treated as missing. |
| `Phone`               | Candidate phone            | No       | Stored as text, not number.                       |
| `File`                | Resume file name/reference | No       | Warn if file is referenced but not supplied.      |

### `Mentors info`

| Source Column | Canonical Meaning   | Required | Validation              |
| ------------- | ------------------- | -------- | ----------------------- |
| `Mentors`     | Mentor display name | Yes      | Non-empty.              |
| `email id`    | Mentor email        | No       | Valid email if present. |

### `Mentors-projects`

| Source Column                  | Canonical Meaning            | Required | Validation                                                    |
| ------------------------------ | ---------------------------- | -------- | ------------------------------------------------------------- |
| `Mentors`                      | Project mentor names         | Yes      | Non-empty; warn if not linkable to `Mentors info`.            |
| `Short profile of the mentor`  | Mentor/project context       | No       | Free text.                                                    |
| `Project Title`                | Project title                | Yes      | Non-empty and unique enough within import batch.              |
| `Project Abstract`             | Project description          | No       | Warn if empty because matching quality may suffer.            |
| `Pre-requisites`               | Required skills/technologies | No       | Parsed into canonical skills/technologies; warn if empty.     |
| `Student's Preference - 1/2/3` | Existing preference marker   | No       | Captured as source signal if meaningful.                      |
| `Selected students`            | Historical/manual selection  | No       | Captured as label/feedback signal, not final system decision. |

### `Probable projects`

Optional backlog input. Rows can be imported as project ideas but are excluded from MVP matching unless explicitly promoted to projects.

---

## 5. Scope

### In Scope

- Import batches and import files.
- Workbook parsing for the reference workbook shape.
- Header aliasing and sheet detection.
- Row-level validation issues.
- Candidate, mentor, project, prerequisite, and preference normalization.
- Resume file registration and candidate linking.
- Resume parsing as optional enrichment.
- Embedding generation for canonical candidate/project profiles.
- Explicit match runs.
- Hybrid scoring with component breakdowns.
- Grounded explanation generation through `ai/generation/`.
- JSON and XLSX result outputs.

### Out of Scope

- Full student registration and login.
- Full mentor dashboard.
- Chat.
- Notifications.
- Admin moderation panel.
- Automatic final project allocation.
- Celery/RQ or distributed worker infrastructure.
- Dedicated vector database.
- Multi-tenant institution isolation.
- Model fine-tuning.

---

## 6. Solution Options and Trade-offs

### Option 1: MVP Script

Read workbook and resumes in a script, generate an output spreadsheet, and manually inspect results.

Trade-offs:

| Dimension          | Assessment             |
| ------------------ | ---------------------- |
| Complexity         | Low initially.         |
| Development effort | Fastest.               |
| Maintainability    | Poor.                  |
| Scalability        | Poor.                  |
| Performance        | Fine for tiny cohorts. |
| Cost               | Low.                   |
| Extensibility      | Poor.                  |

Why rejected:

It does not satisfy Documentation First, Testing First, auditability, or integration needs.

### Option 2: Recommended Production MVP

Build a modular monolith with import batches, validation, canonical tables, match runs, AI services, and exports.

Trade-offs:

| Dimension          | Assessment                             |
| ------------------ | -------------------------------------- |
| Complexity         | Moderate and justified.                |
| Development effort | Medium.                                |
| Maintainability    | Strong.                                |
| Scalability        | Good for MVP; worker extraction later. |
| Performance        | Adequate for cohort-scale matching.    |
| Cost               | Low to moderate.                       |
| Extensibility      | Strong.                                |

Why selected:

It solves the real problem without premature enterprise infrastructure. It aligns with KISS, YAGNI, Clean Architecture, AI Agnostic Design, and Testing First.

### Option 3: Enterprise Pipeline

Use separate ingestion, parsing, feature extraction, matching, evaluation, and export services connected by queues and object storage.

Trade-offs:

| Dimension          | Assessment                      |
| ------------------ | ------------------------------- |
| Complexity         | High.                           |
| Development effort | High.                           |
| Maintainability    | Strong only with a larger team. |
| Scalability        | Excellent.                      |
| Performance        | Excellent at scale.             |
| Cost               | High.                           |
| Extensibility      | Excellent.                      |

Why rejected:

It is premature before workload size, team size, and SLAs justify distributed infrastructure.

### Recommendation

Implement Option 2: a modular monolith production MVP with explicit import and match-run boundaries.

---

## 7. Industry Practice

Startups typically validate this with a structured backend and spreadsheet exports before building a polished portal.

Mid-sized SaaS companies add background workers, review UIs, role-based access, audit logs, and feedback-based evaluation once the workflow is proven.

Large technology companies split this into separate services for ingestion, document processing, ranking, model evaluation, and serving. That architecture is appropriate only when organizational and scale constraints require it.

---

## 8. API Design

Detailed endpoint schemas are drafted in `specs/apis/bulk-intake-and-matching-api.md`. Initial API surface:

| Method | Path                                                          | Description                                             | Auth Required | Role             |
| ------ | ------------------------------------------------------------- | ------------------------------------------------------- | ------------- | ---------------- |
| `POST` | `/api/import-batches`                                         | Create an import batch.                                 | No            | operator         |
| `POST` | `/api/import-batches/{id}/files`                              | Attach workbook/resume files and parse synchronously.   | No            | operator         |
| `GET`  | `/api/import-batches`                                         | Get import batch list and summaries.                    | No            | operator         |
| `GET`  | `/api/candidates`                                             | List candidates.                                        | No            | operator         |
| `GET`  | `/api/projects`                                               | List projects.                                          | No            | operator         |
| `GET`  | `/api/matching/student-recommendations/{registration_number}` | Get project recommendations for an existing student.    | No            | student/operator |
| `POST` | `/api/matching/student-recommendations`                       | Upload resume on-the-fly and fetch matching projects.   | No            | student          |
| `GET`  | `/api/matching/project-recommendations/{project_id}`          | Get recommended students for a specific project.        | No            | mentor/operator  |
| `GET`  | `/api/matching/batch-scores/{batch_id}`                       | Return deterministic matrix scores for the whole batch. | No            | operator         |
| `POST` | `/api/matching/llm-preview`                                   | Preview LLM explanation generation.                     | No            | operator         |

---

## 9. Data Model Changes

### New Tables

```text
import_batches
  id: uuid primary key
  source_system: text nullable
  source_reference: text nullable
  status: enum(created, parsing, validated, failed)
  created_at: timestamp
  completed_at: timestamp nullable

import_files
  id: uuid primary key
  import_batch_id: uuid foreign key
  file_name: text
  file_type: enum(workbook, resume, other)
  storage_path: text
  checksum: text
  status: enum(uploaded, parsed, failed)
  created_at: timestamp

import_validation_issues
  id: uuid primary key
  import_batch_id: uuid foreign key
  import_file_id: uuid foreign key nullable
  sheet_name: text nullable
  row_number: integer nullable
  severity: enum(error, warning)
  code: text
  message: text
  raw_value: text nullable
  created_at: timestamp

candidates
  id: uuid primary key
  import_batch_id: uuid foreign key
  external_candidate_id: text
  full_name: text
  profile_text: text nullable
  github_username: text nullable
  github_metrics: json nullable
  leetcode_username: text nullable
  leetcode_metrics: json nullable
  codeforces_username: text nullable
  codeforces_metrics: json nullable
  scholar_id: text nullable
  scholar_metrics: json nullable
  achievements: json nullable
  created_at: timestamp
  unique(import_batch_id, external_candidate_id)

candidate_contacts
  id: uuid primary key
  candidate_id: uuid foreign key
  email: text nullable
  phone: text nullable

candidate_documents
  id: uuid primary key
  candidate_id: uuid foreign key
  import_file_id: uuid foreign key nullable
  source_file_name: text
  parse_status: enum(pending, complete, failed, skipped)
  parser_name: text nullable
  parser_version: text nullable

candidate_skills
  id: uuid primary key
  candidate_id: uuid foreign key
  skill_id: uuid foreign key
  source: enum(resume, workbook, inferred)
  confidence: numeric nullable

mentors
  id: uuid primary key
  import_batch_id: uuid foreign key
  display_name: text
  profile_text: text nullable

mentor_contacts
  id: uuid primary key
  mentor_id: uuid foreign key
  email: text nullable

projects
  id: uuid primary key
  import_batch_id: uuid foreign key
  title: text
  abstract: text nullable
  status: enum(imported, eligible, excluded)

project_prerequisites
  id: uuid primary key
  project_id: uuid foreign key
  skill_id: uuid foreign key nullable
  raw_text: text
  importance: enum(required, preferred, unknown)

project_preferences
  id: uuid primary key
  project_id: uuid foreign key
  candidate_id: uuid foreign key nullable
  preference_rank: integer nullable
  source_text: text nullable

batch_pair_scores
  id: int primary key
  batch_id: int foreign key
  candidate_id: int foreign key
  project_id: int foreign key
  embedding_similarity: float
  prerequisite_overlap: float
  resume_experience: float
  preference_signal: float
  preliminary_score: float
  computed_at: timestamp
```

Existing or shared tables:

- `skills`
- `technologies`
- `tags`
- `audit_logs`

### Migrations

- [ ] Alembic migration created.
- [ ] `alembic upgrade head` verified on a fresh database.
- [ ] `alembic downgrade base` verified.

---

## 10. Service Design

```python
class ImportBatchService:
    async def create_batch(self, source_system: str | None) -> ImportBatch:
        """Create a new import batch."""

    async def attach_file(self, batch_id: UUID, file: UploadFile) -> ImportFile:
        """Store and register an import file."""

    async def parse_workbooks(self, batch_id: UUID) -> ImportSummary:
        """Parse workbook files and create validation issues."""


class WorkbookImportService:
    async def parse(self, import_file: ImportFile) -> WorkbookParseResult:
        """Map workbook sheets into typed staging rows."""


class NormalizationService:
    async def normalize_batch(self, batch_id: UUID) -> NormalizationSummary:
        """Create canonical candidates, mentors, projects, skills, and prerequisites."""


class ResumeEnrichmentService:
    async def enrich_candidate_documents(self, batch_id: UUID) -> ResumeEnrichmentSummary:
        """Parse linked resumes and enrich candidate profiles."""


class MatchService:
    async def recommend_projects_for_db_candidate(self, registration_number: str) -> StudentRecommendationsResponse:
        """Recommend projects for an existing imported student."""

    async def recommend_projects_for_student(self, resume_bytes: bytes, preferred_topics: list[str]) -> StudentRecommendationsResponse:
        """Parse resume in-memory and recommend projects."""

    async def recommend_candidates_for_project(self, project_id: int) -> ProjectRecommendationsResponse:
        """Recommend students for a project."""

    async def compute_batch_scores(self, batch_id: int, force: bool = False) -> BatchScoreMatrixResponse:
        """Return deterministic (no-LLM) scores for every student×project pair in a batch."""
```

---

## 11. AI / Generation Components

| Component                    | Module                                                 | Prompt Template                 | Fallback                                                                          |
| ---------------------------- | ------------------------------------------------------ | ------------------------------- | --------------------------------------------------------------------------------- |
| Resume parsing               | `ai/parsing/pdf_parser.py`, `ai/parsing/ocr_parser.py` | None                            | Mark document parse failed and continue with workbook data.                       |
| Candidate/project embeddings | `ai/embeddings/`                                       | None                            | Match run fails if required embeddings cannot be generated.                       |
| Reranking                    | `ai/reranking/`                                        | None                            | Continue with semantic and skill scores if reranker is unavailable, with warning. |
| Match explanations           | `ai/generation/match_explanation.py`                   | `prompts/match_explanation.txt` | Deterministic score-based explanation.                                            |

Rules:

- No direct LLM calls from feature services.
- Explanations must include only grounded facts and clearly framed inference.
- AI failure modes must be visible in match-run metadata or validation issues.

---

## 12. Frontend Components

MVP frontend is optional. If built, it is an internal review UI.

### New Pages

| Route                 | Description                        |
| --------------------- | ---------------------------------- |
| `/imports`            | List import batches.               |
| `/imports/new`        | Upload workbook/resume files.      |
| `/batch-score-matrix` | Review batch score matrix heatmap. |

### New Components

| Component              | Purpose                                   |
| ---------------------- | ----------------------------------------- |
| `ImportBatchTable`     | Lists import batches and status.          |
| `ValidationIssueTable` | Displays row-level errors and warnings.   |
| `MatchRunStatus`       | Shows status, timing, and failure reason. |
| `ProjectMatchResults`  | Displays ranked candidates by project.    |
| `ScoreBreakdown`       | Shows component score details.            |

---

## 13. Validation & Test Plan

Full validation plan: `validation.md`.

Summary:

| Test Type   | What Is Tested                      | Expected Outcome                                                              |
| ----------- | ----------------------------------- | ----------------------------------------------------------------------------- |
| Unit        | Header aliasing and sheet detection | Expected sheets/columns resolve from reference workbook.                      |
| Unit        | Row validation                      | Missing/invalid values produce correct issue codes.                           |
| Unit        | Normalization                       | Candidates, mentors, projects, and prerequisites normalize deterministically. |
| Unit        | Scoring formula                     | Fixed inputs produce fixed scores.                                            |
| Unit        | Explanation fallback                | Provider failure returns non-empty deterministic explanation.                 |
| Integration | Import batch lifecycle              | Files attach, parse, validate, and summarize correctly.                       |
| Integration | Match-run lifecycle                 | Run creates persisted results and status transitions.                         |
| Integration | Export endpoint                     | XLSX export contains expected projects, candidates, scores, and warnings.     |

---

## 14. Definition of Done

- [x] ADR-0001 is accepted.
- [x] This feature spec is approved.
- [x] Input workbook contract is documented.
- [x] Data model migration applies and rolls back cleanly.
- [x] Import parser has fixture-based tests using representative workbook rows.
- [x] Validation issues are persisted with sheet and row context.
- [x] Candidate, mentor, project, and prerequisite normalization is tested.
- [x] Resume linking and parse failure behavior is tested.
- [x] Match runs persist status, configuration, results, and explanations.
- [x] JSON and XLSX result outputs are generated from persisted results.
- [x] Unit and integration tests pass.
- [x] No direct LLM calls exist outside `ai/generation/`.
- [x] No production code is implemented before architecture approval.

---

## 15. Open Questions

| Question                                                                                                   | Owner             | Resolution Date | Decision                                                                                                   |
| ---------------------------------------------------------------------------------------------------------- | ----------------- | --------------- | ---------------------------------------------------------------------------------------------------------- |
| Should MVP auth use service API key or service JWT?                                                        | Product/Tech Lead | 2026-06-29      | Neither for MVP. Add operator auth only before public deployment; service auth is deferred to integration. |
| Will resume files be uploaded to ProjectMatchAI or referenced from upstream storage?                       | Product/Tech Lead | 2026-06-29      | Uploaded with the import batch for MVP.                                                                    |
| Should `Selected students` be treated as historical labels, reviewer feedback, or ignored for MVP scoring? | Product/Tech Lead | 2026-06-29      | Store as historical label/source signal only. Do not boost score from it in MVP.                           |
| What is the minimum acceptable export format for program operators?                                        | Product/Tech Lead | 2026-06-29      | Project-centric JSON and XLSX first. Candidate-centric export is deferred.                                 |

---

_This feature is approved for phased implementation. Keep production code aligned with the phase-specific plan and validation checklist._
