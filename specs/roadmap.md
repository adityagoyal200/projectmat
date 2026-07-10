# ProjectMatchAI - Implementation Roadmap

> Constitution Document - Version 5.0 - June 2026
> This roadmap reflects the simplified in-memory ingest and symmetrical matching recommendation architecture for the standalone upload-and-review MVP.

---

## Guiding Principles

- The MVP validates upload, import, matching, explanation, and result review.
- Every phase produces a reviewable artifact.
- Every feature starts with a spec under `specs/features/`.
- Architecture decisions with meaningful trade-offs require ADRs under `specs/adrs/`.
- Tests are part of every phase's Definition of Done.
- Resumes are parsed entirely in-memory; no raw PDF files are stored on disk.
- Symmetrical recommendation endpoints serve both students (by registration number or resume upload) and mentors (by project ID).

---

## Tier Overview

```text
MVP (Phases 0-5)
  Proves: messy candidate/project data can be imported, normalized in-memory, matched, explained, and exported.

Post-MVP A - Operator UX and Deployment Readiness
  Adds: complete review UI, operator auth, deployment hardening, and optional external API contracts.

Post-MVP B - Quality and Feedback
  Adds: reviewer feedback loops, AI evaluation, scoring iteration, and outcome analytics.

Post-MVP C - Portal and Integration Features
  Adds: student/mentor dashboards, roadmaps, chat, notifications, and admin features only if needed.
```

---

## Phase Summary

| Phase   | Name                                         | Status    |
| ------- | -------------------------------------------- | --------- |
| Phase 0 | Project Setup                                | Completed |
| Phase 1 | Data Model                                   | Completed |
| Phase 2 | Bulk Workbook Import                         | Completed |
| Phase 3 | In-Memory Ingest & Profile Normalization     | Completed |
| Phase 4 | Symmetrical Matching & Recommendation APIs   | Completed |
| Phase 5 | Cohort Match Run & Export                    | Completed |
| Phase 6 | Deterministic Profile & Code Quality scoring | Completed |
| Phase 7 | Candidate–Project Fit Report (PDF)           | Completed |

---

# MVP - Phases 0-5

## MVP Goal

A program operator can provide a workbook with student/candidate and project rows.
ProjectMatchAI can then:

- Validate the imported data and extract Google Drive resume links.
- Programmatically download and parse resumes in-memory (no local PDF storage).
- Normalize candidates, mentors, projects, skills, and prerequisites.
- Provide symmetrical recommendation APIs for students (by registration or resume upload) and mentors (by project ID).
- Run explicit match jobs for the entire cohort.
- Produce ranked recommendations per project with score breakdowns and explanations.
- Export results as JSON and XLSX.

---

## Phase 0 - Project Setup

### Goal

Establish a runnable monorepo foundation.

### Status

Completed.

---

## Phase 1 - Data Model

### Goal

Create the normalized relational schema required for import batches, canonical records, match runs, match results, and auditability.

### Status

Completed.

---

## Phase 2 - Bulk Workbook Import

### Goal

Import workbook data into typed staging records with explicit validation issues.

### Status

Completed.

---

## Phase 3 - In-Memory Ingest & Profile Normalization

### Goal

Link candidate records to Google Drive resumes, parse PDFs in-memory without saving them to disk, normalize candidates, mentors, projects, and prerequisites into canonical registries, and expose read discoverability endpoints.

### Deliverables

- Google Drive link extraction in `workbook_parser.py` (Row 25 cell hyperlink) and metadata row skipping (Rows 24-25).
- In-memory PDF downloader and parser (PyMuPDF) integration.
- Staging of candidate name, contact, skills, and profile details directly to the database.
- Normalization of projects, mentors, email links, and prerequisites.
- Discoverability endpoints:
  - `GET /api/candidates` (list and filter candidates).
  - `GET /api/candidates/{id}` (fetch candidate details).
  - `GET /api/projects` (list and filter projects).
  - `GET /api/projects/{id}` (fetch project details).

### Definition of Done

- Import parser correctly extracts the Google Drive resumes link from `pro.xlsx` without errors.
- Resumes are fetched, parsed in-memory, and candidate profiles are successfully created.
- No resume PDF files are stored on disk.
- Candidates and projects list and detail routes return correct database records.
- Unit and integration tests cover in-memory parsing and CRUD endpoints.

### Dependencies

- Phase 2

---

## Phase 4 - Symmetrical Matching & Recommendation APIs

### Goal

Generate embeddings for candidates and projects, retrieval using pgvector, and build symmetrical student and mentor matching recommendation APIs with qualitative LLM reasoning.

### Status

Completed.

### Deliverables

- Candidate and project serialization + embedding service integration (BGE-M3 or configured API).
- pgvector semantic retrieval.
- Hybrid scoring pipeline (semantic similarity, adjacent skills, candidate preferences boost).
- Symmetrical recommendation routers:
  - `GET /api/matching/student-recommendations/{registration_number}` (retrieve matches for existing student).
  - `POST /api/matching/student-recommendations` (accept resume PDF, parse in-memory, match on-the-fly for new student).
  - `GET /api/matching/project-recommendations/{project_id}` (retrieve student matches for a specific project).
- Qualitative LLM evaluation prompts and deterministic score-based fallback explanations.

### Definition of Done

- Students can query project recommendations by registration number or by uploading a resume.
- Mentors can query candidate recommendations by project ID.
- Recommendations return ranked lists, score breakdowns, and human-like explanations.
- Unit tests verify preference boosts and LLM fallback logic.

### Dependencies

- Phase 3

---

## Phase 5 - Cohort Match Run & Export

### Goal

Run explicit, cohort-wide deterministic matrix score generation and expose an interactive BatchScoreMatrix UI.

### Status

Completed.

### Deliverables

- Batch Score Matrix list and detail endpoints (`GET /api/import-batches` and `GET /api/matching/batch-scores/{batch_id}`).
- Deterministic database caching via `batch_pair_scores` table to avoid repeating score generation.
- Interactive, responsive Student Tile Grid UI in the frontend:
  - Big composite scores and progress bars color-coded by strength (strong/moderate/weak).
  - All 4 sub-scores (Embed, Prereq, Resume, Pref) always visible side-by-side.
  - Sorters (Best, Average, A-Z) and expandable project recommendations list.
  - Automatic loading when any batch card is selected.

### Definition of Done

- Batch score matrix is generated, persisted, and cached in the database without LLM call latency.
- Matrix UI renders candidate tiles and color-coded score indicators.

### Dependencies

- Phase 4

---

## Phase 6 - GitHub Repository & Live App Evaluation

### Goal

Perform a comprehensive review of candidate projects through profile extraction, static repository analysis, optional isolated execution, live app testing, and browser-agent-style observation traces.

### Status

Completed.

### Deliverables

- Resume profile extraction for GitHub repositories, GitHub usernames, LeetCode, Codeforces, Kaggle, Google Scholar, live project links, and achievement lines.
- Candidate persistence for developer profile handles, profile metrics, repository links, live app links, and achievements.
- Repository and live app evaluation persistence with API endpoints under `/api/evaluations`.
- Deterministic repository inspector for local checkouts and optional remote clone mode:
  - Source structure and language counts.
  - README, license, and dependency manifest checks.
  - Automated test discovery with explicit opt-in execution.
  - Secret-pattern scanning.
  - Structured findings and execution logs.
- Live app evaluator for HTTP reachability, status, latency, title, visible error text, loading-state signals, and Reason -> Act -> Observe traces.
- Phase 6 deterministic score components integrated into recommendations and batch score caching (scoring v3.1.0 weights, per `backend/app/config.py`):
  - GitHub/repository/live quality: 30%.
  - Coding profiles: 5%.
  - Achievements and Scholar signals: 5%.
  - LLM qualitative fit: 5%.
  - Embedding 15%, prerequisite 20%, and resume experience 20% retained.
  - _Note: coding-profile and achievement weights were retuned down (from an earlier 20%/10% draft) to 5%/5% as GitHub/repository quality proved the stronger deterministic signal._

### Definition of Done

- Parsed resumes populate developer profile fields without storing raw PDF files.
- Candidate and batch evaluation endpoints return persisted repository/live-app evaluations.
- Matching recommendations and batch scores include Phase 6 deterministic components.
- Repository test execution and remote cloning are explicit opt-in operations.
- Backend tests, backend lint, and frontend build/lint checks pass.

### Original Requirements

1. **Repository Evaluation**
   The platform performs a comprehensive review of the project's source code using a combination of static analysis, automated execution, and AI-based code understanding. It examines:

   - Overall code structure, logic, and architectural design.
   - Presence and execution of automated tests.
   - Code quality, maintainability, and adherence to coding standards.
   - Security practices, including detection of exposed secrets and poor git hygiene.
   - Documentation quality, particularly the availability of a properly structured README.
     To execute tests and analysis, the evaluator creates isolated environments, installs project dependencies automatically, and runs standard development tools.

2. **Live Application Evaluation**
   The deployed application is tested from an end-user perspective rather than solely through code inspection. The system verifies:

   - Whether required UI components and features are present.
   - Whether user interactions (clicks, form submissions, uploads, etc.) function correctly.
   - Overall application stability, responsiveness, and ability to recover from hosting sleep states.
   - Absence of persistent loading issues, crashes, or visible frontend errors.

3. **Multimodal AI-Powered Testing**
   Instead of relying on fragile HTML selectors or traditional web scrapers, the evaluator uses autonomous AI browser agents that can:

   - Analyze both screenshots and accessibility data.
   - Identify interface elements visually.
   - Interact with applications through a reasoning-driven workflow.
   - Continuously observe outcomes and adjust actions based on results.
     This approach allows the system to behave similarly to a human QA tester while remaining resilient to frontend implementation changes.

4. **Autonomous Browser Agent Workflow**
   The browser agent operates using a Reason → Act → Observe loop:

   - Understands the current screen.
   - Decides the next interaction.
   - Performs the action in a real browser.
   - Observes the updated state.
   - Repeats until the feature has been validated.

5. **Dynamic Test Data Generation**
   When applications require user inputs such as file uploads, the evaluator can automatically generate realistic mock files (e.g., PDFs) within a secure temporary environment and use them during testing.

6. **Background Task Orchestration**
   Resource-intensive operations such as repository cloning and security scanning are executed asynchronously through CLI-based task orchestration. This enables the evaluator to continue processing other checks efficiently while long-running tasks execute in the background.

### Dependencies

- Phase 5

---

## Phase 7 - Candidate–Project Fit Report (PDF)

### Goal

Let an operator download a self-contained, print-ready PDF that explains why a specific
candidate fits a specific project and how the candidate should close their gaps —
combining the deterministic factor breakdown with an LLM-generated readiness analysis.

### Status

Completed.

### Deliverables

- `GET /api/matching/report?registration_number=&project_id=` streaming a PDF
  (`application/pdf`, `Content-Disposition: attachment`).
- `MatchService.build_match_report(...)` reusing the full scoring path for the factor
  breakdown (scoring v3.1.0) plus one LLM analysis call.
- `app/features/matching/report.py`: `generate_improvement_analysis` (structured JSON:
  fit summary, in-depth assessment, strengths, gaps, improvement plan, learning roadmap,
  recommended resources, project approach, mentor risks; deterministic-skeleton
  fallback), `build_report_html` (Story-safe HTML), and `render_html_to_pdf`
  (PyMuPDF `fitz.Story`, rendered off-thread; `ReportRenderError` on failure).
- Frontend `lib/api/report.ts::downloadMatchReport` wired into `RecommendationCard`.
- No new dependency (PyMuPDF already used for resume parsing) and no schema change
  (the report is computed on the fly, nothing persisted).

### Definition of Done

- Endpoint returns a valid PDF for a real candidate–project pair (verified end-to-end).
- LLM failure degrades to a deterministic factor-only PDF instead of a `500`.
- OpenAPI docs expose the endpoint; backend/frontend lint clean.
- Unit + integration tests cover the report logic, retry semantics, and `404`/`503`
  paths (`tests/unit/test_report.py`, `tests/integration/test_matching_api.py`); the
  analysis call retries transient LLM failures before falling back to the deterministic
  skeleton. Deferred: a full `200` happy-path integration test.
  See `specs/features/2026-07-03-candidate-project-fit-report/`.

### Dependencies

- Phase 4 (scoring path, LLM evaluation), Phase 6 (developer-profile factors).

---

# Post-MVP & Backlog

Refer to previous specs and Backlog for details on UI operator consolidation, feedback loop systems, and vector search fine-tuning.
