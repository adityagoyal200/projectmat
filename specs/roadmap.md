# ProjectMatchAI — Implementation Roadmap

> **Constitution Document · Version 3.0 · June 2026**
> This roadmap defines the incremental implementation strategy for ProjectMatchAI. It is split into three tiers: the **MVP**, which proves the core AI matching hypothesis with minimal scope; **Post-MVP Phases A & B**, which build the user experience once the AI is validated; and **Phase C**, which adds platform maturity, evaluation, and production hardening.

---

## Guiding Principles

- **Phases are small**: Each phase targets 1–3 days of focused work
- **Tests in every phase**: Unit and integration tests are part of every phase's Definition of Done
- **YAGNI strictly enforced**: No feature is built before it appears in the current tier
- **The MVP exists to answer one question**: Can AI match students to projects better than manual review?
- **Every new feature follows the templates in `specs/templates/`**

---

## Tier Overview

```
MVP (Phases 0–13)
  Proves: AI matching pipeline works end-to-end
  Deliverable: A mentor can see AI-ranked student candidates with explanations

Post-MVP Phase A — Student Experience
  Adds: Student-facing dashboards, skill gap, roadmap, and career reports

Post-MVP Phase B — Mentor Experience
  Adds: Mentor dashboard, accept/reject UI, notifications

Post-MVP Phase C — Platform Maturity
  Adds: Chat, feedback, AI evaluation, admin, deployment
```

---

## MVP Phase Summary (0–13)

| Phase    | Name                                 | Status         |
| -------- | ------------------------------------ | -------------- |
| Phase 0  | Project Setup                        | 🔲 Not Started |
| Phase 1  | Database Schema                      | 🔲 Not Started |
| Phase 2  | Authentication — Backend             | 🔲 Not Started |
| Phase 3  | Authentication — Frontend            | 🔲 Not Started |
| Phase 4  | Resume Upload                        | 🔲 Not Started |
| Phase 5  | Resume Parsing — PDF                 | 🔲 Not Started |
| Phase 6  | Resume Parsing — OCR                 | 🔲 Not Started |
| Phase 7  | Student Profile                      | 🔲 Not Started |
| Phase 8  | Project Creation                     | 🔲 Not Started |
| Phase 9  | Embedding Service                    | 🔲 Not Started |
| Phase 10 | Vector Search                        | 🔲 Not Started |
| Phase 11 | Cross Encoder Reranking              | 🔲 Not Started |
| Phase 12 | Hybrid Scoring                       | 🔲 Not Started |
| Phase 13 | Generation Service + LLM Explanation | 🔲 Not Started |

## Post-MVP Phase Summary

| Phase       | Name                                | Status         |
| ----------- | ----------------------------------- | -------------- |
| **Phase A** | **Student Experience**              |                |
| A1          | Student Dashboard & Recommendations | 🔲 Not Started |
| A2          | Skill Gap & Learning Roadmap        | 🔲 Not Started |
| A3          | ATS & Industry Readiness Reports    | 🔲 Not Started |
| **Phase B** | **Mentor Experience**               |                |
| B1          | Mentor Dashboard & Candidate Review | 🔲 Not Started |
| B2          | Notifications                       | 🔲 Not Started |
| **Phase C** | **Platform Maturity**               |                |
| C1          | Chat                                | 🔲 Not Started |
| C2          | Feedback                            | 🔲 Not Started |
| C3          | AI Evaluation Framework             | 🔲 Not Started |
| C4          | Admin Panel                         | 🔲 Not Started |
| C5          | End-to-End Testing                  | 🔲 Not Started |
| C6          | Production Deployment               | 🔲 Not Started |

---

# MVP — Phases 0–13

> **Goal**: A mentor can log in, create a project, and see AI-ranked student candidates with plain-language explanations. Nothing else.

---

## Phase 0 — Project Setup

### Goal

Establish a fully functional, runnable project skeleton with all tooling configured. Every subsequent phase builds on this foundation.

### Deliverables

**Repository & Tooling**

- Monorepo structure: `/frontend`, `/backend`, `/specs`
- `README.md` with setup instructions
- `.gitignore`, `.env.example`
- GitHub repository initialised with `main` branch protection

**Backend**

- FastAPI application scaffolded: `app/main.py`, `app/config.py`, `app/database.py`, `app/dependencies.py`
- Poetry dependency management with `pyproject.toml`
- Pydantic `Settings` class wired to `.env` via `pydantic-settings`
- SQLAlchemy 2.0 async engine + `asyncpg` driver
- Alembic initialised (`alembic init alembic/`)
- Structlog configured: structured JSON in production, coloured in dev; `request_id` middleware
- Global exception handler returning consistent error shape
- Health check endpoint: `GET /api/health`
- Pre-commit hooks: ruff, pyright

**Frontend**

- Vite + React 18 with TypeScript: `npm create vite@latest frontend -- --template react-ts`
- Tailwind CSS and shadcn/ui base components (`Button`, `Input`, `Card`)
- React Router v6 installed
- ESLint + Prettier configured
- `src/lib/api/client.ts` — typed fetch wrapper with base URL, auth header, and error handling
- `src/App.tsx` — root component with router and `QueryClientProvider`
- `vercel.json` with SPA rewrite: `{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }`

**Infrastructure**

- `docker-compose.yml`: `db` (PostgreSQL + pgvector), `ollama`
- SQLAlchemy engine verified connecting to Docker PostgreSQL

### Definition of Done

- `docker compose up` starts all services without error
- `GET /api/health` returns `{ "status": "ok" }`
- `npm run build` succeeds with zero TypeScript or lint errors
- Ruff passes with zero warnings
- Pre-commit hooks run successfully on a test commit

### Dependencies

None.

---

## Phase 1 — Database Schema

### Goal

Define and apply the complete normalised database schema. All tables are created now to prevent migration conflicts in later phases. No business data lives in JSON columns.

### Deliverables

**SQLAlchemy Models** (in `app/features/*/models.py`)

_Identity_

- `users` — id, email, password_hash, role (`student`|`mentor`|`admin`), google_id, is_active, is_verified, created_at

_Skill & Technology Registries_

- `skills` — id, name (unique, indexed), category, is_verified
- `technologies` — id, name (unique, indexed), ecosystem
- `tags` — id, name (unique, indexed), tag_type

_Student Profile_

- `student_profiles` — id, user_id (FK unique), headline, bio, status (`draft`|`confirmed`), profile_embedding (Vector(1024)), embedding_model_version, updated_at
- `student_skills` — id, student_id (FK), skill_id (FK), level, years_experience
- `student_technologies` — id, student_id (FK), technology_id (FK), proficiency

_Projects_

- `projects` — id, mentor_id (FK), title, description, difficulty, timeline_weeks, status (`draft`|`open`|`closed`), project_embedding (Vector(1024)), created_at
- `project_required_skills` — id, project_id (FK), skill_id (FK), minimum_level
- `project_preferred_skills` — id, project_id (FK), skill_id (FK)
- `project_tags` — id, project_id (FK), tag_id (FK)

_Matching_

- `matches` — id, project_id (FK), student_id (FK), composite_score, semantic_score, rerank_score, skill_overlap_score, explanation (Text), status (`pending`|`accepted`|`rejected`), created_at

_Resume_

- `resume_uploads` — id, user_id (FK), file_path, parse_status, parse_method (`pdf`|`ocr`), parsed_at

_Post-MVP tables (created now, populated later)_

- `roadmap_steps` — id, student_id, project_id, skill_id (FK), resource_type, estimated_hours, order, completed
- `notifications` — id, recipient_id (FK), type, title, body, metadata (JSON), is_read, created_at
- `chat_messages` — id, match_id (FK), sender_id (FK), content, sent_at
- `feedback` — id, match_id (FK unique), mentor_id (FK), rating (1–5), strengths, growth_areas, project_completed, created_at
- `evaluation_runs` — id, run_at, dataset_version, precision_at_10, recall_at_10, ndcg, mrr
- `evaluation_queries` — id, run_id (FK), query_project_id (FK), relevant_student_ids (Array), retrieved_student_ids (Array)
- `audit_logs` — id, actor_id (FK), action, target_type, target_id, metadata (JSON), created_at

**Migrations**

- Alembic initial migration: `alembic revision --autogenerate -m "initial_schema"`
- `alembic upgrade head` verified on fresh database
- `alembic downgrade base` verified

### Definition of Done

- All models defined with proper relationships, indexes, unique constraints, and `__repr__`
- `alembic upgrade head` and `alembic downgrade base` both complete cleanly
- All foreign key constraints validated

### Dependencies

- Phase 0

---

## Phase 2 — Authentication — Backend

### Goal

Implement email/password registration, Google OAuth, JWT issuance, and role-based access control.

### Deliverables

**Endpoints**

- `POST /api/auth/register` — creates user, sends verification email
- `POST /api/auth/login` — returns access token + refresh token cookie
- `POST /api/auth/refresh` — exchanges refresh token for new access token
- `POST /api/auth/logout` — clears refresh token cookie
- `GET /api/auth/me` — returns current user
- `GET /api/auth/verify-email/{token}` — activates account
- `GET /api/auth/google` — redirects to Google OAuth
- `GET /api/auth/google/callback` — issues JWT after OAuth

**Implementation**

- `passlib` (bcrypt cost 12) for password hashing
- `python-jose` for JWT encode/decode
- `slowapi` for rate limiting (10 req/min on login)
- `httpx` for Google token exchange
- `get_current_user` and `require_role()` FastAPI dependencies in `app/dependencies.py`

**Tests**

- Unit: JWT encode/decode, password hashing, role enforcement
- Integration: all 8 endpoints with `httpx.AsyncClient`

### Definition of Done

- All auth endpoints return correct status codes
- Invalid credentials → 401; missing token → 401; wrong role → 403
- Google OAuth flow creates a user and issues a JWT
- Email verification activates account

### Dependencies

- Phase 0, Phase 1

---

## Phase 3 — Authentication — Frontend

### Goal

Implement all authentication UI flows and wire them to the backend.

### Deliverables

**Pages**: `/auth/register`, `/auth/login`, `/auth/logout`

**Implementation**

- `AuthContext` — `user`, `login()`, `logout()`, `isLoading`
- `useAuth()` hook
- `ProtectedRoute` component — redirects to `/auth/login` if unauthenticated; accepts optional `role` prop
- Google OAuth button → redirect to `/api/auth/google`
- Refresh token handled transparently in `src/lib/api/client.ts`

**UI**: Premium Tailwind + shadcn/ui forms, inline validation, loading states

### Definition of Done

- Register → login → protected page flow works end-to-end
- Unauthenticated users redirect to `/auth/login`
- Google OAuth completes successfully

### Dependencies

- Phase 2

---

## Phase 4 — Resume Upload

### Goal

Enable students to upload a PDF resume for parsing.

### Deliverables

**Backend**

- `POST /api/profile/resume` — validates PDF, ≤ 5MB; stores file; creates `resume_uploads` record with `parse_status="pending"`

**Frontend**

- Drag-and-drop upload page (`react-dropzone`), progress indicator, client-side validation

**Tests**

- Unit: file type and size validation
- Integration: upload endpoint with test PDF

### Definition of Done

- PDF stored; database record created
- Invalid type or oversized files rejected with clear errors

### Dependencies

- Phase 3

---

## Phase 5 — Resume Parsing — PDF

### Goal

Extract structured profile data from digital PDFs.

### Deliverables

**`ai/parsing/pdf_parser.py`**

- `PDFParser` using PyMuPDF (`fitz`)
- `parse_to_profile(file_path) -> ParsedProfile`
- `ParsedProfile`: full_name, email, skills (list[str]), technologies (list[str]), experience, education, raw_text, parse_method

**Endpoint**

- `POST /api/profile/parse/{upload_id}` — triggers parsing, updates `parse_status`

**Tests**

- Unit: section detection with fixture text
- Integration: full parse flow on a sample PDF

### Definition of Done

- Digital PDF → `ParsedProfile` with non-empty skills and experience
- `parse_status` updated to `"complete"` or `"failed"`

### Dependencies

- Phase 4

---

## Phase 6 — Resume Parsing — OCR

### Goal

Fallback OCR parser for scanned or image-based PDFs.

### Deliverables

**`ai/parsing/ocr_parser.py`**

- `OCRParser` using PaddleOCR
- `ParsingService` orchestrates: try PDF first → fall back to OCR if < 100 characters extracted
- `parse_method` set to `"ocr"` when OCR path is taken

**Tests**

- Unit: fallback logic (mock PDF parser returning empty string)
- Integration: scanned PDF sample produces parseable output

### Definition of Done

- Scanned PDF produces `ParsedProfile` via OCR fallback
- OCR failures are caught as structured errors (no 500s)

### Dependencies

- Phase 5

---

## Phase 7 — Student Profile

### Goal

Enable students to review, edit, and confirm their AI-generated profile, with skills resolved to the canonical `skills` and `technologies` tables.

### Deliverables

**Backend**

- `GET /api/profile/me` — profile with skills (from `student_skills`), technologies, experience
- `PUT /api/profile/me` — updates fields
- `POST /api/profile/me/skills` — add skill (resolved to `skills` table)
- `DELETE /api/profile/me/skills/{skill_id}`
- `POST /api/profile/me/technologies` — add technology
- `DELETE /api/profile/me/technologies/{technology_id}`
- `POST /api/profile/me/confirm` — sets status to `"confirmed"`, triggers embedding (Phase 9)

**Frontend**

- `/student/profile` — profile editor with skill tag autocomplete, level selectors, confirm button

**Tests**

- Unit: skill resolution (exact match → fuzzy match → create)
- Integration: all profile endpoints

### Definition of Done

- Student can view, edit, and confirm profile
- Skills stored in `student_skills` join table (not JSON)
- Profile transitions `draft` → `confirmed`

### Dependencies

- Phase 6

---

## Phase 8 — Project Creation

### Goal

Enable mentors to create projects with normalised skill requirements.

### Deliverables

**Backend**

- `POST /api/projects`, `GET /api/projects`, `GET /api/projects/{id}`, `PUT /api/projects/{id}`, `DELETE /api/projects/{id}` (soft delete)
- Required and preferred skills stored in `project_required_skills` and `project_preferred_skills` (not JSON)
- Tags stored in `project_tags`

**Frontend**

- `/mentor/projects/new`, `/mentor/projects`, `/mentor/projects/{id}` with skill autocomplete

**Tests**

- Integration: all CRUD endpoints

### Definition of Done

- Mentor can create/edit/delete projects
- Skills stored in join tables
- Projects in `"open"` status are eligible for matching

### Dependencies

- Phase 3

---

## Phase 9 — Embedding Service

### Goal

Generate and store dense vector embeddings for confirmed student profiles and open projects.

### Deliverables

**`ai/embeddings/bge.py`**

- `BGEEmbeddingService` (BAAI/BGE-M3 via `sentence-transformers`)
- `embed_text(text: str) -> list[float]`
- Model loaded once at startup via `app.state`
- Profile serialisation: skills, technologies, experience concatenated in a consistent format

**Triggers**

- Profile confirmation (`POST /api/profile/me/confirm`) generates student embedding
- Project status change to `"open"` generates project embedding

**Tests**

- Unit: text serialisation format
- Integration: embedding stored correctly in `profile_embedding` / `project_embedding`

### Definition of Done

- Confirmed profiles and open projects have non-null embeddings
- `embedding_model_version` recorded alongside every vector

### Dependencies

- Phase 7, Phase 8

---

## Phase 10 — Vector Search

### Goal

Retrieve the top-K semantically similar student profiles for a given project.

### Deliverables

**`app/features/matching/services.py`**

- `VectorSearchService.retrieve_candidates(project_id, top_k=50) -> list[CandidateResult]`
- pgvector cosine similarity with HNSW index

**Database**: HNSW indexes on `profile_embedding` and `project_embedding`

**Tests**

- Integration: retrieval returns correct number of candidates with scores in [0, 1]

### Definition of Done

- Vector search returns up to 50 candidates
- Query latency < 500ms on 1,000 student profiles

### Dependencies

- Phase 9

---

## Phase 11 — Cross Encoder Reranking

### Goal

Reorder top-K candidates using a BGE Cross Encoder for improved precision.

### Deliverables

**`ai/reranking/bge_reranker.py`**

- `BGEReranker.rerank(query, candidates) -> list[RankedCandidate]`
- Loaded at startup via `app.state`

**Tests**

- Unit: reranker output ordering with mocked scores
- Integration: reranked list differs from raw similarity order

### Definition of Done

- 50 candidates → reordered top-20
- Reranker latency < 2 seconds on CPU

### Dependencies

- Phase 10

---

## Phase 12 — Hybrid Scoring

### Goal

Combine semantic, reranker, and skill overlap signals into a single composite score.

### Deliverables

**`ai/matching/hybrid_scorer.py`**

- `HybridScorer.score(candidate, project) -> ScoredCandidate`
- Three signals:
  - **Semantic score** (w1 = 0.4): pgvector cosine similarity
  - **Rerank score** (w2 = 0.4): BGE Reranker score
  - **Skill overlap score** (w3 = 0.2): fraction of required skills in `student_skills` join table
- All weights configurable via `Settings`
- Interface accepts optional `feedback_score`, `learning_feasibility_score` kwargs for future extension

**Endpoint**

- `GET /api/projects/{project_id}/candidates` — returns scored and ranked candidates

**Tests**

- Unit: scoring formula with fixed inputs
- Unit: skill overlap using normalised join tables
- Integration: full pipeline returns ranked list

### Definition of Done

- Candidates returned with `composite_score` and component breakdown
- Scores stored in `matches` table
- Scorer interface does not need to change when post-MVP signals are added

### Dependencies

- Phase 11

---

## Phase 13 — Generation Service + LLM Explanation

### Goal

Introduce the `ai/generation/` module as the single, centralised gateway for all LLM-generated text in the application. Implement LLM explanations for matched candidates as the first generation feature.

### Why a Dedicated Generation Module

Instead of calling the LLM provider directly from `matching/`, `reports/`, `roadmap/`, and any other feature service, all generation goes through `ai/generation/`. This provides:

- **Centralised prompt management** — all prompts live in `ai/generation/prompts/`
- **Centralised retries and error handling** — one place to implement exponential backoff
- **Provider-agnostic** — the `LLMProvider` interface is injected; no generation module knows whether it is talking to Groq or Ollama
- **Easier testing** — mock the `LLMProvider`, test prompt construction separately
- **Lower maintenance** — adding a new generation feature requires adding one file, not touching multiple services

### Deliverables

**`ai/providers/`**

- `LLMProvider` abstract base class: `generate(prompt: str) -> str`, `health_check() -> bool`
- `GroqProvider(LLMProvider)` — default for dev and cloud staging
- `OllamaProvider(LLMProvider)` — for self-hosted deployments
- Provider instantiated at startup via `app.state.llm_provider`

**`ai/generation/`**

```
ai/generation/
  base.py          # GenerationService base class; takes LLMProvider from app.state
  explanation.py   # ExplanationGenerator — produces match explanations
  prompts/
    explanation.txt  # Prompt template for match explanation
```

**`ai/generation/base.py`**

```python
class GenerationService:
    def __init__(self, provider: LLMProvider): ...
    async def _generate_with_fallback(self, prompt: str, fallback_fn: Callable) -> str:
        """Calls provider; on any exception, calls fallback_fn and returns its result."""
```

**`ai/generation/explanation.py`**

```python
class ExplanationGenerator(GenerationService):
    async def generate(self, candidate: ScoredCandidate, project: Project) -> str:
        """Returns 100–200 word plain-English explanation grounded in candidate skills and project requirements."""
```

**`ai/generation/prompts/explanation.txt`**

```
You are an expert academic advisor. Given a student profile and a project description,
explain in 2–3 sentences why this student is a good match.

Student skills: {student_skills}
Student experience: {student_experience}

Project: {project_title}
Required skills: {required_skills}
Match scores: semantic={semantic_score}, skill_overlap={skill_overlap_score}

Provide a concise, factual, encouraging explanation.
```

**Endpoint update**

- `GET /api/projects/{project_id}/candidates` — includes `explanation` per candidate

**Tests**

- Unit: prompt construction with mock profile and project (no LLM call)
- Unit: graceful degradation — when `LLMProvider.generate()` raises, returns non-empty fallback string
- Integration: full pipeline returns non-empty explanations (Groq mocked for CI)

### Definition of Done

- `ai/generation/` module exists and `ExplanationGenerator` is the only code that calls the LLM for explanations
- Every candidate returned by `GET /api/projects/{project_id}/candidates` has a non-empty `explanation`
- LLM unavailability returns a fallback template explanation — no 500
- `LLM_PROVIDER=groq` and `LLM_PROVIDER=ollama` both produce valid explanations

### MVP Complete ✅

At the end of Phase 13, a mentor can:

1. Log in
2. Create a project with required skills
3. View AI-ranked student candidates, each with a composite score breakdown and a plain-language explanation

This validates the core product hypothesis. Everything after this is user experience and platform maturity.

### Dependencies

- Phase 12

---

# Post-MVP — Phase A: Student Experience

> Builds the student-facing experience on top of the validated AI pipeline.

---

## Phase A1 — Student Dashboard & Recommendations

### Goal

Build the student-facing landing experience: profile status, AI-recommended projects, and match scores.

### Deliverables

**Backend**

- `GET /api/student/recommendations` — projects ranked by match score for the current student (inverts the pipeline: student embedding as query, project embeddings as corpus)
- `GET /api/student/skill-gap/{project_id}` — skills the student has vs. what the project requires

**Frontend**

- `/student/dashboard` — profile completion prompt, recommended projects, match scores
- `/student/projects` — browseable open projects with match scores
- `/student/projects/{id}` — project detail with skill gap summary

**Components**: `ProjectCard`, `SkillGapSummary`, `ProfileCompletion` progress indicator

### Definition of Done

- Recommendations are personalised and ranked
- Skill gap uses `student_skills` vs `project_required_skills` (normalised tables)

### Dependencies

- Phase 13

---

## Phase A2 — Skill Gap & Learning Roadmap

### Goal

Generate a personalised learning roadmap stored in `roadmap_steps`, with steps linked to specific skills.

### Deliverables

**`ai/generation/roadmap.py`** — `RoadmapGenerator(GenerationService)`

- Generates a learning roadmap description for each missing skill
- Uses `ai/generation/prompts/roadmap.txt`

**Backend**

- `GET /api/student/roadmap/{project_id}` — generates `roadmap_steps` records, returns structured `LearningRoadmap`
- `POST /api/student/roadmap/{project_id}/steps/{step_id}/complete` — marks step complete

**Frontend**

- `/student/roadmap/{project_id}` — timeline view of skills to learn, mark-as-complete

### Definition of Done

- Each `roadmap_step` linked to `skill_id` FK (not free text)
- `RoadmapGenerator` goes through `ai/generation/` — not a direct LLM call in the profile service

### Dependencies

- Phase A1

---

## Phase A3 — ATS & Industry Readiness Reports

### Goal

Generate career-supporting reports for students.

### Deliverables

**`ai/generation/ats.py`** — `ATSGenerator(GenerationService)`, prompt: `prompts/ats.txt`
**`ai/generation/readiness.py`** — `ReadinessGenerator(GenerationService)`, prompt: `prompts/readiness.txt`

**Backend**

- `GET /api/student/reports/ats` — ATS keyword coverage, profile completeness score, formatting recommendations
- `GET /api/student/reports/readiness` — skills benchmarked against role demand, recommended next steps

**Frontend**

- `/student/reports` — ATS and readiness report hub

### Definition of Done

- Both generators extend `GenerationService` base class
- All LLM calls go through `ai/generation/`, not direct provider calls in the reports service

### Dependencies

- Phase A1

---

# Post-MVP — Phase B: Mentor Experience

---

## Phase B1 — Mentor Dashboard & Candidate Review

### Goal

Build the mentor-facing UI for project management and AI-ranked candidate review with accept/reject actions.

### Deliverables

**Backend**

- `POST /api/matches/{match_id}/accept` — accepts student; triggers `match.accepted` notification (Phase B2)
- `POST /api/matches/{match_id}/reject` — rejects student; triggers `match.rejected` notification

**Frontend**

- `/mentor/dashboard` — active projects summary, pending reviews
- `/mentor/projects/{id}/candidates` — ranked candidate list with score breakdown, AI explanation, accept/reject buttons
- `CandidateCard`, `ScoreBreakdown`, `ExplanationPanel` components

### Definition of Done

- Mentor can view candidates, read explanations, and accept or reject
- Accept/reject updates match status in `matches` table

### Dependencies

- Phase 13, Phase A1

---

## Phase B2 — Notifications

### Goal

Implement in-app notifications for key events, delivered over WebSocket when the recipient is online.

### Deliverables

**`app/features/notifications/`**

- `NotificationService.create(recipient_id, type, title, body, metadata=None)`
- Called by existing services at appropriate moments (B1 accept/reject, A1 resume parse, C2 feedback)

**Endpoints**

- `GET /api/notifications` — paginated, unread first
- `POST /api/notifications/{id}/read`
- `POST /api/notifications/read-all`
- `GET /api/notifications/unread-count`

**Notification Types**

- `match.accepted`, `match.rejected` (wired in B1)
- `resume.parsed` (wired in Phase 5–6)
- `feedback.received` (wired in C2)
- `project.deadline_approaching` (scheduled background task — post-MVP)

**Real-time delivery**

- If recipient has an active WebSocket connection, push `{ "type": "notification", "data": ... }`
- Otherwise, stored for next load

**Frontend**

- Notification bell with badge, dropdown list, toast pop-ups for live notifications

### Definition of Done

- `match.accepted` and `match.rejected` notifications created by B1
- `resume.parsed` notification created by Phase 5–6
- Unread count updates after mark-as-read

### Dependencies

- Phase B1

---

# Post-MVP — Phase C: Platform Maturity

---

## Phase C1 — Chat

### Goal

Real-time WebSocket chat between matched student ↔ mentor pairs, sharing the WebSocket connection used by notifications.

### Deliverables

**Backend**

- `WebSocket /api/chat/{match_id}` — authenticates via token query param; validates participant membership; persists messages; delivers notification pushes on same connection
- `GET /api/chat/{match_id}/history` — paginated message history

**Frontend**

- `/chat/{match_id}` — real-time chat UI with history

### Definition of Done

- Student and mentor can exchange messages after match is accepted
- Messages persisted and retrievable after page refresh
- Unauthenticated connections rejected
- `message.received` notification created for the other participant

### Dependencies

- Phase B2

---

## Phase C2 — Feedback

### Goal

Enable mentors to submit post-project feedback, creating a signal for future recommendation improvements.

### Deliverables

**Backend**

- `POST /api/matches/{match_id}/feedback` — rating (1–5), strengths, growth_areas, project_completed
- `GET /api/matches/{match_id}/feedback` — mentor + admin only

**Frontend**

- Feedback form in mentor dashboard after project marked complete
- Student can view received feedback in their profile

### Definition of Done

- Feedback stored in `feedback` table (FK to `matches`)
- `feedback.received` notification created for student
- `HybridScorer` interface ready to accept feedback score as optional kwarg (groundwork done)

### Dependencies

- Phase C1

---

## Phase C3 — AI Evaluation Framework

### Goal

Implement an offline evaluation framework to measure AI matching quality. This is a research and improvement tool — not a user-facing feature.

### Deliverables

**`ai/evaluation/`**

```
ai/evaluation/
  dataset.py   # Load ground-truth relevance judgements from accepted matches + feedback
  metrics.py   # Pure functions: precision_at_k, recall_at_k, ndcg_at_k, mrr
  runner.py    # Orchestrates run; stores results in evaluation_runs; prints delta report
```

**Metrics**

| Metric           | Definition                                                      |
| ---------------- | --------------------------------------------------------------- |
| **Precision@10** | Fraction of top-10 retrieved students that are relevant         |
| **Recall@10**    | Fraction of all relevant students appearing in top-10           |
| **NDCG**         | Ranking quality — higher-ranked relevant items contribute more  |
| **MRR**          | Average of 1/rank of the first relevant item across all queries |

**CLI**

- `python -m ai.evaluation.runner --dataset-version v1`

**Tests**

- Unit: all metric functions with hardcoded inputs and expected values
- Integration: `EvaluationRunner.run()` completes on a test dataset

**Target Baselines**

| Metric       | Target |
| ------------ | ------ |
| Precision@10 | ≥ 0.40 |
| Recall@10    | ≥ 0.30 |
| NDCG         | ≥ 0.50 |
| MRR          | ≥ 0.50 |

### Definition of Done

- All metric functions unit-tested with known expected values
- `EvaluationRunner.run()` stores results in `evaluation_runs` table
- Delta report shows comparison to previous run
- CLI entrypoint works

### Dependencies

- Phase C2 (feedback data exists for ground truth)

---

## Phase C4 — Admin Panel

### Goal

Provide admins with basic user and project management. For MVP, use `psql` or the Supabase Dashboard directly — this phase builds a lightweight custom admin panel.

### Deliverables

**Backend**

- `GET /api/admin/users`, `PUT /api/admin/users/{id}/status`
- `GET /api/admin/projects`, `PUT /api/admin/projects/{id}/status`
- `GET /api/admin/stats`
- All endpoints write to `audit_logs` table
- All endpoints protected by `require_role("admin")`

**Frontend**

- `/admin` — stats dashboard (user count, project count, match count)
- `/admin/users` — user management with status toggle
- `/admin/projects` — project moderation

### Definition of Done

- Admin can activate/deactivate users and moderate projects
- All admin actions recorded in `audit_logs`
- Non-admin requests return 403

### Dependencies

- Phase 3, Phase 8

---

## Phase C5 — End-to-End Testing

### Goal

Validate the complete integrated system through Playwright E2E tests.

### E2E Scenarios

- **Student flow**: register → upload resume → confirm profile → view recommendations → view skill gap → view roadmap
- **Mentor flow**: login → create project → view ranked candidates → read explanations → accept student → chat → submit feedback
- **Notification flow**: accept match triggers notification badge update for student
- **Admin flow**: login → view users → deactivate test user → view projects → flag test project

### Definition of Done

- All scenarios pass on three consecutive runs
- E2E suite completes in < 10 minutes
- Any regression causes CI to fail

### Dependencies

- All Phases C1–C4

---

## Phase C6 — Production Deployment

### Goal

Deploy the production system to Vercel (frontend), Railway (backend), and Supabase (database).

### Deliverables

**Infrastructure**

- Vercel: `frontend/` root, `vercel.json` SPA rewrite, production environment variables
- Railway: `backend/` Dockerfile, production environment variables
- Supabase: pgvector extension enabled, `alembic upgrade head` applied

**CI/CD (GitHub Actions)**

- `lint.yml` — Ruff, ESLint, type checks on every push
- `test.yml` — unit and integration tests on every push
- `eval.yml` — AI evaluation runner on every change to `ai/`; fails if metrics drop below baseline
- `deploy-frontend.yml` — deploys to Vercel on merge to `main`
- `deploy-backend.yml` — deploys to Railway on merge to `main`

**Monitoring**

- Structured logs in Railway log explorer
- Vercel analytics for frontend performance

### Definition of Done

- Production accessible at a public URL
- All Phase C5 E2E tests pass against production
- AI evaluation CI job passes with metrics above baseline
- No secrets committed to the repository

### Dependencies

- Phase C5

---

## Post-MVP Backlog (Future/)

| Feature                             | Notes                                                                                  |
| ----------------------------------- | -------------------------------------------------------------------------------------- |
| Microsoft OAuth                     | Add second social provider                                                             |
| Email notifications                 | Celery + Redis + SendGrid; async on `Notification` creation                            |
| Feedback-weighted scoring           | Wire `feedback.rating` into `HybridScorer` after sufficient data                       |
| Learning feasibility scoring        | LLM-based: "can this student learn X in N weeks?" — use `ai/generation/feasibility.py` |
| Longitudinal student profiles       | Track skill growth across multiple projects                                            |
| Mentor reputation scoring           | Derived from student feedback ratings                                                  |
| Fine-tuned embedding models         | Domain-specific BGE fine-tuning on platform feedback data                              |
| Redis pub/sub for WebSocket scaling | Required when multiple backend instances are deployed                                  |
| Cohort analytics for institutions   | Aggregate skill and gap data per institution                                           |
| OpenAI provider                     | Add `OpenAIProvider` — zero business logic changes                                     |
| AI evaluation CI gate               | Block deployments when metrics drop below threshold                                    |

---

_This document was authored as part of the ProjectMatchAI project constitution. Update it as phases are completed or re-scoped._
