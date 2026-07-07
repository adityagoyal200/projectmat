# ProjectMatchAI - Technology Stack

> Constitution Document - Version 3.0 - June 2026
> This document defines the approved technology choices for ProjectMatchAI after the scope shift to a standalone bulk intake and AI matching app.

---

## 1. Architecture Style

### Selected: Modular Monolith with Explicit Frontend/Backend Boundary

ProjectMatchAI remains a single backend and operator frontend in one monorepo. The system is organized by feature/domain. The frontend uploads files and reviews results; the backend owns parsing, validation, normalization, matching, explanations, persistence, and export.

Why selected:

- Keeps development simple for MVP.
- Supports clear module boundaries without microservice overhead.
- Allows future external integration only if a larger platform needs it.
- Aligns with YAGNI and KISS from `specs/00-principles.md`.

Rejected alternatives:

- Separate services for ingestion, parsing, matching, and export: too much operational complexity for MVP.
- Notebook/script-based matching pipeline: fast initially but not testable, observable, or production-safe.
- Full student/mentor portal first: contradicts the upload-and-review MVP.

---

## 2. Repository Layout

```text
projectmatchai/
  backend/
    app/
      features/
        imports/        # import batches, files, validation issues
        candidates/     # student/candidate canonical records
        mentors/        # mentor canonical records
        projects/       # project canonical records and prerequisites
        matching/       # match runs, results, scoring orchestration
        exports/        # spreadsheet/API result export
      ai/
        parsing/        # resume parsers and OCR adapters
        extraction/     # structured profile/project extraction
        embeddings/     # embedding service interface and providers
        reranking/      # cross-encoder reranking
        generation/     # centralized LLM-generated explanations
        evaluation/     # offline match-quality evaluation
      config.py
      database.py
      dependencies.py
      main.py
  frontend/
    src/
      pages/            # optional internal review/import UI
      components/
      lib/api/
  specs/
    adrs/
    features/
    templates/
```

Rules:

- Route handlers call services only.
- Services coordinate repositories, parsers, AI services, and exporters.
- Repositories own persistence.
- AI modules do not import FastAPI or feature internals.

---

## 3. Backend

### FastAPI with Python 3.11+

FastAPI remains the backend framework.

Why selected:

- Strong typed request/response models through Pydantic.
- Async support for database, file, and model-provider calls.
- Automatic OpenAPI documentation for the frontend and future integration consumers.
- Python-native AI, document parsing, and spreadsheet ecosystem.

Expected usage:

- Import batch APIs.
- Match-run APIs.
- Export APIs.
- Health and readiness endpoints.
- Optional internal review UI APIs.

### Pydantic v2

Used for:

- API schemas.
- Import row schemas.
- Validation error structures.
- Match-run configuration schemas.

### SQLAlchemy 2.0 Async + Alembic

Used for:

- Canonical relational models.
- Import batch and validation issue persistence.
- Match-run and result history.
- Migration management.

---

## 4. Database

### PostgreSQL 15+ with pgvector

PostgreSQL remains the primary database and vector store for MVP.

Why selected:

- Relational constraints are essential for normalized candidates, mentors, projects, and match runs.
- pgvector avoids introducing a separate vector database before scale requires it.
- Alembic supports controlled schema evolution.

### Schema Principles

No business-critical structured data should live only in JSON.

Expected core tables:

| Area       | Tables                                                                                                |
| ---------- | ----------------------------------------------------------------------------------------------------- |
| Imports    | `import_batches`, `import_files`, `import_validation_issues`                                          |
| Candidates | `candidates`, `candidate_contacts`, `candidate_documents`, `candidate_skills`, `candidate_embeddings` |
| Mentors    | `mentors`, `mentor_contacts`, `mentor_project_links`                                                  |
| Projects   | `projects`, `project_prerequisites`, `project_preferences`, `project_embeddings`                      |
| Matching   | `match_runs`, `match_results`, `match_result_explanations`                                            |
| Shared     | `skills`, `technologies`, `tags`, `audit_logs`                                                        |
| Evaluation | `repository_evaluations`, `live_app_evaluations`                                                      |

JSON columns are allowed only for:

- Source row snapshots for audit/debug.
- External API payload snapshots.
- Variable metadata that is not queried as business data.

---

## 5. Spreadsheet Ingestion

### Selected: `openpyxl` for XLSX, Python `csv` for CSV

Why selected:

- Direct Python support in the FastAPI backend.
- Handles workbook sheets, cell values, merged headers, and basic formatting metadata.
- Simple enough for MVP and easy to unit test with fixture workbooks.

Usage:

- Read `.xlsx` workbook inputs.
- Map known sheets and headers into typed row schemas.
- Preserve source sheet, row number, and raw row snapshot for audit.

Rules:

- Parsing is isolated in `features/imports/parsers/`.
- Header aliases are versioned and documented.
- Validation errors are explicit records, not exceptions hidden in logs.
- Production matching never reads directly from spreadsheet rows; it reads canonical database records.

Rejected alternatives:

- Pandas as production ingestion layer: useful for analysis, but less explicit for typed validation and source-row error reporting.
- Ad hoc CSV/XLSX parsing inside services: hard to test and maintain.

---

## 6. Resume and Document Parsing

### PyMuPDF

Primary parser for digital PDF resumes.

### PaddleOCR

Fallback parser for scanned PDFs or image-heavy resumes.

Rules:

- Resume parsing output becomes a structured candidate profile draft.
- Raw parser output is not canonical profile data.
- Parser confidence and failure reasons are stored.
- Resume parsing is optional enrichment; imported spreadsheet fields still create candidate records.

---

## 6.1. Developer Profiles & Live Application Evaluation

### Scraping Clients

To enrich candidate developer profiles, lightweight clients fetch metrics from:

- **GitHub REST API**: Stars, followers, repositories, and pull requests/OS contributions.
- **LeetCode GraphQL API**: Submissions count (categorized by easy/medium/hard difficulty) and contest stats.
- **Codeforces REST API**: Ranks and competitive ratings.
- **Google Scholar (HTML Regex parser)**: Citation count, h-index, and publication records.

### Static Repository Analyzer & Test Runner

Static code inspection is executed locally or via cloned remote repositories.

- Secrets detection (Regex key/token signatures).
- Dependency manifest identification (`package.json`, `requirements.txt`, etc.).
- Automated test framework detection (npm test, pytest).
- Isolated test command execution (using `subprocess` limits and timeouts).

### Playwright Headless Browser Crawls

Live application URLs are verified from an end-user perspective using:

- **Playwright Chromium**: A headless browser session that navigates to live app endpoints.
- **Wakeup Timeout Tolerance**: Wait limits up to 45 seconds to handle server cold starts (Render/Streamlit).
- **Tab Interaction**: Simulated clicks on primary dashboard tabs to test hydration.
- **Console Log Listeners**: Observes browser console error/exception counts.
- **Screenshots**: High-resolution PNG captures saved locally to serve as audit proof.

---

## 7. AI Providers and Generation

### Abstract Provider Interface

All LLM calls go through a provider interface.

Initial providers:

- Groq for development and hosted staging.
- Ollama for self-hosted/local deployments where appropriate.
- Gemini and OpenAI are also supported behind the same interface.

### Centralized Generation Layer

All LLM-generated text goes through `ai/generation/`.

Initial generators:

- `MatchExplanationGenerator`
- Future: `CandidateProfileExtractor`, `ProjectRequirementExtractor`, `LearningGapGenerator`

Rules:

- No feature service calls an LLM provider directly.
- Prompt templates live in `ai/generation/prompts/`.
- Fallback text is deterministic and tested.

---

## 8. Embeddings and Reranking

### Embeddings

Selected default: BAAI BGE-M3 through `sentence-transformers`.

Usage:

- Candidate profile embeddings.
- Project description/prerequisite embeddings.

Every embedding stores:

- Source record id.
- Source record version.
- Model name/version.
- Schema version.
- Generated timestamp.

### Vector Search

Selected default: pgvector HNSW indexes with cosine distance.

MVP retrieval:

- For each project, retrieve top-K candidate profiles.
- Default retrieval pool: 50 candidates, configurable.

### Reranking

Status: deferred. `match_results` reserves `reranker_version`/`reranker_score` columns for this, but no reranker is implemented — scoring currently combines embedding similarity, prerequisite overlap, resume evidence, and the developer-profile signals from `specs/adrs/ADR-0001-standalone-bulk-intake-matching-mvp.md` instead. Revisit if retrieval-pool precision becomes a measured bottleneck.

Planned default if implemented: BGE cross-encoder reranker, reranking the retrieved candidate pool against the full project context and feeding a reranker score into the hybrid score.

---

## 9. Matching

### Match-Run Model

Matching is performed through explicit match runs.

Each `match_run` records:

- Import batch id.
- Scoring configuration version.
- Candidate/project filters.
- Embedding model version.
- Reranker version.
- Generation provider/model version.
- Status: `queued`, `running`, `completed`, `failed`, `cancelled`.

### Hybrid Score

Initial component signals:

- Semantic similarity.
- Reranker relevance.
- Skill/prerequisite overlap.
- Resume evidence coverage.
- Student/project preference signal when available.

Future component signals:

- Mentor feedback.
- Historical outcome quality.
- Learning feasibility.

Rules:

- Component scores are stored with final score.
- Weights are configuration-driven and logged per run.
- Ranking must remain explainable.

---

## 10. Background Processing

### MVP: In-Process Match Runner

MVP can use FastAPI background tasks or a controlled in-process runner for import parsing and match-run execution.

Why:

- Current cohorts are small enough that distributed orchestration is unnecessary.
- A status table still gives observability.
- The design can migrate later without changing API contracts.

Future replacement:

- Celery/RQ with Redis if match runs exceed request/worker limits.
- Dedicated worker service if parsing and matching load becomes independent from API traffic.

---

## 11. Frontend

### Vite + React 18 + TypeScript

The frontend is now optional internal tooling, not the primary MVP product surface.

Expected MVP usage:

- Upload/import review screen.
- Validation issue review.
- Match-run status.
- Ranked result review and export.

Deferred:

- Full student dashboard.
- Full mentor dashboard.
- Chat.
- Notifications.
- Public-facing pages.

### Tailwind CSS + shadcn/ui

Still selected for internal UI because it is fast, accessible, and consistent with the existing repo.

---

## 12. Authentication and Authorization

### MVP: No Application Auth

The first MVP is an operator-run upload-and-review app. Authentication is deferred until public deployment or external integration requires it.

Rules:

- Do not add JWT, OAuth, password hashing, or rate-limiting dependencies before the auth phase.
- Do not store browser tokens in the frontend before a real auth design exists.
- If the app is deployed outside a trusted/local environment, complete the operator auth hardening phase first.

Future options:

- Simple operator login for standalone deployment.
- Service API key or service JWT for a larger platform integration.

---

## 13. Exports

Initial export formats:

- XLSX result workbook for program operators.
- JSON API response for the frontend and future integrations.

Export content:

- Project.
- Ranked candidates.
- Component scores.
- Explanation.
- Warnings or missing-data notes.
- Match-run metadata.

Rules:

- Exports are generated from persisted match results, not recomputed ad hoc.
- Export schemas are versioned.

---

## 14. Logging and Observability

Selected: `structlog`.

Required structured events:

- `import.started`
- `import.validation_failed`
- `import.completed`
- `resume.parse_failed`
- `match_run.started`
- `match_run.completed`
- `match_run.failed`
- `ai.provider_failed`
- `export.generated`

Every import, parse, match, and export log must include a request id or job id.

---

## 15. Testing Strategy

Backend:

- `pytest`
- `pytest-asyncio`
- `httpx.AsyncClient`
- Fixture workbooks and resumes

Frontend:

- Vitest
- React Testing Library
- Playwright only when the UI becomes important enough to justify E2E coverage

AI evaluation:

- Precision@K.
- Recall@K.
- NDCG.
- MRR.
- Agreement with historical mentor selections when labels exist.

---

## 16. Deployment

MVP:

- Backend: Railway or equivalent container hosting.
- Database: Supabase PostgreSQL with pgvector.
- Frontend: Vercel static SPA if internal review UI is used.

Future:

- Dedicated worker process for parsing/matching.
- Object storage for resume files.
- Redis for distributed jobs and websocket scaling only when measured need exists.

---

## 17. Configuration

All environment variables are centralized in `app/config.py`.

Expected categories:

- Database connection.
- Import limits.
- Resume storage path or object storage settings.
- LLM provider settings.
- Embedding and reranking model settings.
- Match scoring weights.
- Auth credentials only after the auth hardening or external integration phase.
- Logging level and environment.

---

_This document should be updated when a technology choice changes or when external integration becomes active roadmap scope._
