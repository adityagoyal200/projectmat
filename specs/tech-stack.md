# ProjectMatchAI — Technology Stack

> **Constitution Document · Version 2.0 · June 2026**
> This document defines every technology choice made for ProjectMatchAI, including rationale, alternatives considered, trade-offs, and future replacement strategies. Treat this as a living reference — update it when any dependency changes.

---

## Table of Contents

1. [Architecture Style](#1-architecture-style)
2. [Frontend](#2-frontend)
3. [Backend](#3-backend)
4. [Database](#4-database)
5. [Authentication](#5-authentication)
6. [AI Models](#6-ai-models)
7. [Embeddings](#7-embeddings)
8. [Resume Parsing](#8-resume-parsing)
9. [OCR](#9-ocr)
10. [Vector Search](#10-vector-search)
11. [Reranking](#11-reranking)
12. [AI Evaluation](#12-ai-evaluation)
13. [Notifications](#13-notifications)
14. [Chat (Realtime)](#14-chat-realtime)
15. [Deployment](#15-deployment)
16. [Development Tools](#16-development-tools)
17. [Project Structure](#17-project-structure)
18. [Coding Standards](#18-coding-standards)
19. [Testing Strategy](#19-testing-strategy)
20. [Dependency Injection](#20-dependency-injection)
21. [Configuration Management](#21-configuration-management)
22. [Logging](#22-logging)
23. [Error Handling](#23-error-handling)
24. [Future Scalability](#24-future-scalability)

---

## 1. Architecture Style

### Selected: Monorepo with Feature-Based Structure

**Description**
A single Git repository contains both the frontend (`/frontend`) and backend (`/backend`) codebases. Each codebase is internally organised by feature/domain rather than by technical layer.

**Why Selected**

- Keeps AI-assisted development context local: an agent working on the `matching` feature reads only the `matching/` directory
- Simplifies cross-cutting refactors (rename a type that touches both FE and BE in one PR)
- Consistent tooling, CI/CD, and documentation in one place
- Ideal for a solo developer with AI coding agents

**Alternatives Considered**

- _Separate repos_: Better for large teams with independent deployment cycles; overkill for MVP
- _Layer-based structure_: `controllers/`, `services/`, `repositories/` — harder for AI agents to build context, mixes features

**Trade-offs**

- Can become unwieldy if the team grows significantly without governance

**Future Replacement Strategy**
If team size grows beyond 10 engineers, migrate to a Turborepo-managed monorepo with explicit package boundaries per domain.

---

## 2. Frontend

### Vite + React 18 (SPA)

**Why Selected**

- ProjectMatchAI is a fully authenticated application — every page requires a logged-in user. SSR and SEO are irrelevant; a pure SPA is the simplest correct choice.
- Vite provides near-instant dev server startup and hot module replacement
- React 18 is the industry standard; familiar to most developers and AI coding agents
- Deploys as a static bundle to any CDN: Vercel, Netlify, GitHub Pages, Cloudflare Pages
- No framework-specific concepts (no App Router, no Server Components, no middleware)

**Alternatives Considered**

- _Next.js (App Router)_: Correct for public-facing sites needing SSR/SEO; overkill for a fully authenticated SPA
- _Create React App_: Deprecated; Vite is the successor

**Trade-offs**

- Client-side routing requires a `vercel.json` rewrite rule to serve `index.html` for all paths
- Bundle size must be managed manually (`React.lazy` + `Suspense` for route-level code splitting)

**Expected Usage**
All user-facing pages: student dashboard, mentor dashboard, admin panel, auth flows, chat interface.

**Future Replacement Strategy**
No near-term replacement. If public-facing marketing pages are added post-MVP, create a separate static site rather than migrating the app.

---

### TypeScript

**Why Selected**

- Catches type errors at compile time — critical for a complex domain model (profiles, embeddings, scoring)
- Improves AI-assisted development: agents can infer intent from types without reading full implementations

**Trade-offs**

- Additional compilation step; stricter initial setup

---

### Tailwind CSS v3

**Why Selected**

- Utility-first CSS eliminates class naming overhead
- Excellent integration with shadcn/ui
- PurgeCSS built in — production bundles are small

**Future Replacement Strategy**
Migrate to Tailwind CSS v4 when it reaches stable release and shadcn/ui supports it fully.

---

### shadcn/ui

**Why Selected**

- Copy-paste component library built on Radix UI primitives — components live in the codebase, not a node_modules black box
- Full Tailwind + TypeScript compatibility
- Accessible by default (WAI-ARIA via Radix)
- Highly customisable — not constrained by a third-party design system

**Alternatives Considered**

- _Material UI_: Heavy, opinionated, difficult to theme
- _Chakra UI_: Good DX but runtime CSS-in-JS

---

## 3. Backend

### FastAPI (Python 3.11+)

**Why Selected**

- Native async support (`async`/`await`) — essential for concurrent AI inference calls (embedding generation, reranking, LLM explanation all happening in parallel)
- Automatic OpenAPI schema generation from Python type hints — every endpoint self-documents
- Pydantic v2 models serve as both request/response validation and documentation
- The AI/ML Python ecosystem (transformers, sentence-transformers, PaddleOCR) is Python-native — co-locating AI and API avoids network hops and serialisation overhead
- FastAPI's `Depends()` dependency injection is clean and testable
- Active community with production-proven adoption in AI/ML-heavy services

**Alternatives Considered**

- _Django Ninja_: Provides Django Admin and allauth for free, but Django's ORM lacks mature async support for complex queries; the admin benefit doesn't justify the added conventions for a solo developer
- _Django REST Framework_: Synchronous by default; requires significant async workarounds
- _Node.js (Express/Fastify)_: Would require a separate Python service for AI — adds operational complexity
- _Go (Gin/Fiber)_: Excellent performance, but no mature ML ecosystem

**Trade-offs**

- No built-in admin panel — requires custom implementation (Phase 20)
- No built-in auth — requires manual JWT + OAuth implementation (Phase 2)
- Python's GIL limits true parallelism; mitigated by async I/O and Uvicorn + Gunicorn workers

**Expected Usage**
All REST API endpoints: auth, profile, project creation, matching pipeline, WebSocket chat, notifications, feedback, admin.

**Future Replacement Strategy**
No near-term replacement. If throughput bottlenecks emerge, extract high-load AI services into dedicated async microservices.

---

## 4. Database

### PostgreSQL 15+

**Why Selected**

- Proven, battle-tested relational database with strong ACID guarantees
- `pgvector` extension enables vector similarity search in the same database — eliminates the need for a separate vector database at MVP scale
- Excellent tooling: Alembic migrations, schema introspection, full-text search

**Alternatives Considered**

- _MySQL_: No native vector support; weaker JSON capabilities
- _MongoDB_: Schema flexibility is appealing but eventual consistency is a poor fit for transactional matching data

**Trade-offs**

- Requires careful index management for vector search at scale
- Hosting cost on managed services scales with storage and connections

**Expected Usage**
All structured data: users, profiles, projects, embeddings, matches, chat messages, notifications, feedback, audit logs.

**Future Replacement Strategy**
At very high vector search volume (millions of records), evaluate migrating embeddings to a dedicated vector store (Qdrant, Weaviate) while keeping relational data in PostgreSQL.

---

### pgvector

**Why Selected**

- PostgreSQL extension that adds `vector` data type and similarity operators (`<->`, `<=>`, `<#>`)
- Enables cosine, L2, and inner product similarity search
- Supports HNSW and IVFFlat indexing for approximate nearest neighbour (ANN) search
- Eliminates a separate vector database service for MVP

**Future Replacement Strategy**
Migrate embeddings to Qdrant if query latency exceeds acceptable thresholds at scale.

---

### Normalised Schema Design

**Principle: No business data in JSON columns**

Structured entities must exist as proper relational tables with foreign keys, indexes, and constraints. JSON columns are reserved for unstructured or highly variable data (e.g., raw OCR output, external API payloads).

| Table                      | Purpose                                         | Key Fields                                                                                                          |
| -------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `users`                    | Authentication and identity                     | id, email, password_hash, role, is_active                                                                           |
| `student_profiles`         | Student career profile                          | user_id (FK), headline, bio, status, embedding_model_version                                                        |
| `skills`                   | Canonical skill registry                        | id, name (unique), category, is_verified                                                                            |
| `student_skills`           | Student ↔ Skill join table                     | student_id, skill_id, level, years_experience                                                                       |
| `technologies`             | Technology/tool registry                        | id, name (unique), ecosystem                                                                                        |
| `student_technologies`     | Student ↔ Technology join table                | student_id, technology_id, proficiency                                                                              |
| `tags`                     | Flexible tagging for projects and profiles      | id, name (unique), tag_type                                                                                         |
| `project_tags`             | Project ↔ Tag join table                       | project_id, tag_id                                                                                                  |
| `projects`                 | Mentor-created projects                         | id, mentor_id, title, description, difficulty, timeline_weeks, status                                               |
| `project_required_skills`  | Required skills for a project                   | project_id, skill_id, minimum_level                                                                                 |
| `project_preferred_skills` | Preferred skills for a project                  | project_id, skill_id                                                                                                |
| `matches`                  | AI-generated student-project matches            | id, project_id, student_id, composite_score, semantic_score, rerank_score, skill_overlap_score, explanation, status |
| `resume_uploads`           | Uploaded resume files                           | id, user_id, file_path, parse_status, parse_method                                                                  |
| `roadmap_steps`            | Learning roadmap steps per student-project pair | id, student_id, project_id, skill_id, resource_type, estimated_hours, order, completed                              |
| `notifications`            | In-app notification records                     | id, recipient_id, type, title, body, metadata (JSON), is_read, created_at                                           |
| `chat_messages`            | Real-time chat between matched pairs            | id, match_id, sender_id, content, sent_at                                                                           |
| `feedback`                 | Post-project mentor feedback                    | id, match_id, mentor_id, rating, strengths, growth_areas, project_completed                                         |
| `audit_logs`               | Immutable admin action log                      | id, actor_id, action, target_type, target_id, metadata (JSON), created_at                                           |
| `evaluation_runs`          | AI evaluation execution records                 | id, run_at, dataset_version, precision_at_10, recall_at_10, ndcg, mrr                                               |
| `evaluation_queries`       | Per-query evaluation results                    | id, run_id, query_project_id, relevant_student_ids (Array), retrieved_student_ids (Array)                           |

**Why Separate Tables Instead of JSON**

- Foreign key constraints enforce referential integrity that JSON cannot provide
- Individual skills and technologies can be searched, filtered, and indexed efficiently
- Schema changes (add a field to `skills`) don't require application-level migration of JSON blobs
- The `audit_logs` and `notifications` tables use `metadata JSON` only for variable, schema-free payload data — not for structured entities

---

## 5. Authentication

### JWT (JSON Web Tokens)

**Why Selected**

- Stateless authentication aligns with serverless deployment (Vercel + Railway)
- Easy to implement role-based access control (student, mentor, admin) via claims
- Well-supported in FastAPI via `python-jose` and custom `Depends()` functions

**Trade-offs**

- Token revocation requires a deny-list or short expiry + refresh token pattern

**Expected Usage**
Access tokens (15 min expiry) + refresh tokens (7-day expiry, stored in HTTP-only cookies).

---

### Google OAuth 2.0

**Why Selected**

- Reduces friction for users who prefer social login
- Delegates credential management to Google — reduces security surface area

**Implementation**

- Backend initiates the OAuth flow (`GET /api/auth/google`)
- Google redirects to callback endpoint (`GET /api/auth/google/callback`)
- Backend exchanges code for user info, creates or links a user record, issues JWT

**Future Replacement Strategy**
Add Microsoft OAuth (university SSO) in a post-MVP phase.

---

### Email/Password

**Why Selected**

- Fallback for users without Google accounts

**Security Implementation**

- Passwords hashed with `bcrypt` (cost factor 12) via `passlib`
- Email verification required before account activation
- Rate limiting on login endpoints (10 requests/minute per IP via `slowapi`)

---

## 6. AI Models

### LLM: Abstract Provider Interface

**Design**
All LLM calls route through an abstract `LLMProvider` interface:

```
LLMProvider
  ├── generate(prompt: str, context: dict) -> str
  └── health_check() -> bool

GroqProvider(LLMProvider)   # development + cloud staging (free, fast)
OllamaProvider(LLMProvider) # self-hosted production
```

Provider is selected via `LLM_PROVIDER` environment variable (`groq` | `ollama`). No provider-specific logic leaks into business services. Adding `OpenAIProvider` requires only one new class.

---

### Groq API (llama-3.1-8b-instant or Qwen2.5-7b)

**Why Selected**

- Free tier with generous rate limits — effectively zero cost during development
- OpenAI-compatible API — `GroqProvider` implementation is minimal
- ~500 tokens/second inference speed — eliminates latency of local LLM calls in dev
- No GPU VRAM consumed locally — BGE-M3 and Reranker use the full 4GB VRAM budget on RTX 3050

**Trade-offs**

- External API dependency in development (requires internet + Groq API key)
- Groq free tier: ~30 requests/minute; sufficient for development

**Expected Usage**
Primary LLM provider for development and cloud staging.

---

### Ollama (Qwen2.5 7B)

**Why Selected**

- Zero API cost and zero external dependency for self-hosted deployments
- Ollama's REST API is OpenAI-compatible — `OllamaProvider` is minimal

**Hardware Context (RTX 3050, 4GB VRAM)**

- Qwen2.5 7B in Q4 quantization: ~4–4.5GB VRAM
- With BGE-M3 + Reranker also loaded, total VRAM exceeds 4GB → use Groq in dev to avoid contention
- Ollama is recommended when deploying to a server with 8GB+ VRAM

**Expected Usage**
Self-hosted production deployments.

---

## 7. Embeddings

### BAAI BGE-M3 (via sentence-transformers)

**Why Selected**

- State-of-the-art multilingual dense embedding model
- 8192 token context window — handles full student profiles and project descriptions
- Open source and runs locally — no per-query cost
- Consistently top-ranked on MTEB (Massive Text Embedding Benchmark)

**Trade-offs**

- Large model size (~570MB) — requires sufficient server memory (~2GB RAM)
- Initial load time; mitigated by keeping the model loaded in memory at startup

**Expected Usage**
Generating embeddings for student profiles and project descriptions. Stored in PostgreSQL via pgvector.

**Future Replacement Strategy**
Evaluate newer BGE models or domain-fine-tuned variants as they release.

---

## 8. Resume Parsing

### PyMuPDF (fitz)

**Why Selected**

- Fast, accurate text extraction from digital PDFs
- Pure Python, no external service dependency

**Trade-offs**

- Poor results on scanned or image-based PDFs → handed off to PaddleOCR

**Expected Usage**
Primary parser for all uploaded PDF resumes. Falls back to PaddleOCR if insufficient text is extracted.

---

## 9. OCR

### PaddleOCR

**Why Selected**

- High accuracy on printed and handwritten text
- Runs locally — no external API cost
- Handles complex layouts better than Tesseract

**Trade-offs**

- Large dependency footprint (PaddleOCR + PaddlePaddle ~600MB)
- GPU recommended for acceptable throughput; CPU mode is slower

**Expected Usage**
Fallback OCR for scanned or image-based PDFs.

---

## 10. Vector Search

### pgvector (PostgreSQL Extension)

**Search Configuration**

- Index type: HNSW (`m=16`, `ef_construction=64`) for approximate nearest neighbour
- Distance metric: Cosine similarity (`<=>`)
- Initial retrieval pool: Top-K (configurable, default 50 candidates) before reranking

```sql
SELECT student_id, profile_embedding <=> query_embedding AS similarity_score
FROM student_profiles
ORDER BY profile_embedding <=> query_embedding
LIMIT 50;
```

---

## 11. Reranking

### BGE Reranker v2 (Cross Encoder)

**Why Selected**

- Cross-encoder models compute a relevance score by jointly encoding the query (project description) and each candidate (student profile) — far more accurate than bi-encoder similarity alone
- Significantly improves precision in the top-10 results over embedding-only retrieval
- Open source, runs locally

**Trade-offs**

- Slower than bi-encoders (O(N) inference vs. cached embeddings)
- Acceptable at MVP scale (top-50 candidates per query)

**Expected Usage**
Reranks the top-50 candidates from pgvector semantic search before final hybrid scoring.

---

## 12. Generation Service

### Design

All LLM-generated text in the application routes through the `ai/generation/` module — not through individual feature services. Features like matching, roadmap, ATS reports, and readiness reports each call a dedicated generator class; none of them interact directly with the `LLMProvider`.

```
ai/generation/
  base.py          # GenerationService — takes LLMProvider from app.state; provides _generate_with_fallback()
  explanation.py   # ExplanationGenerator — match explanations for candidates
  roadmap.py       # RoadmapGenerator — learning roadmap steps per missing skill
  ats.py           # ATSGenerator — ATS compatibility report content
  readiness.py     # ReadinessGenerator — industry readiness report content
  prompts/
    explanation.txt
    roadmap.txt
    ats.txt
    readiness.txt
```

**`GenerationService` base class**

```python
class GenerationService:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def _generate_with_fallback(
        self,
        prompt: str,
        fallback_fn: Callable[[], str]
    ) -> str:
        try:
            return await self.provider.generate(prompt)
        except Exception:
            log.warning("llm.generation_failed", fallback=True)
            return fallback_fn()
```

**Benefits**

- **Centralised prompt management**: all prompts live in `ai/generation/prompts/` — not scattered across feature services
- **Centralised retries and error handling**: `_generate_with_fallback()` is implemented once
- **Provider-agnostic**: generator classes do not know whether they are talking to Groq or Ollama
- **Easier testing**: mock `LLMProvider` at the generator level; test prompt construction with pure functions
- **Lower maintenance**: adding a new LLM feature = one new file in `ai/generation/`

**Adding a new generation feature**

1. Create `ai/generation/<feature>.py` extending `GenerationService`
2. Add the prompt template to `ai/generation/prompts/<feature>.txt`
3. Inject the generator via `app.state` or FastAPI `Depends()`
4. Call it from the feature service — never call `LLMProvider` directly

---

## 13. AI Evaluation

### Purpose

The AI matching pipeline must be measurable. Without an evaluation framework, it is impossible to know whether a change to the embedding model, reranker, or hybrid scorer improved or degraded matching quality. This section defines the evaluation infrastructure that makes the AI portion of the project academically rigorous and continuously improvable.

---

### Evaluation Dataset

An offline evaluation dataset is constructed from historical mentor decisions:

- **Queries**: Open projects (each project is a query)
- **Relevant items**: Students whom the mentor accepted or rated highly in feedback (ground-truth relevance)
- **Corpus**: All student profiles in the system at the time of evaluation
- **Dataset versions**: Each evaluation run records the dataset version so results are reproducible

The dataset is stored in the `evaluation_runs` and `evaluation_queries` tables.

---

### Metrics

| Metric                                           | Definition                                                                           | Why It Matters                                                  |
| ------------------------------------------------ | ------------------------------------------------------------------------------------ | --------------------------------------------------------------- |
| **Precision@10**                                 | Fraction of top-10 retrieved students that are relevant                              | Measures the quality of the top candidates shown to a mentor    |
| **Recall@10**                                    | Fraction of all relevant students that appear in the top-10                          | Measures whether good candidates are being missed               |
| **NDCG (Normalised Discounted Cumulative Gain)** | Measures ranking quality — higher-ranked relevant items contribute more to the score | Captures the ordering within the ranked list, not just presence |
| **MRR (Mean Reciprocal Rank)**                   | Average of 1/rank of the first relevant item across all queries                      | Measures how quickly the first good match appears               |

**Target baseline (MVP):**

- Precision@10 ≥ 0.4
- Recall@10 ≥ 0.3
- NDCG ≥ 0.5
- MRR ≥ 0.5

These baselines are intentionally conservative for a cold-start system. They should improve as the evaluation dataset grows.

---

### Evaluation Pipeline

```
evaluation_run.py
  1. Load evaluation dataset (project queries + relevant student sets)
  2. For each query project:
       a. Run vector search → top-50 candidates
       b. Run reranker → reordered top-20
       c. Apply hybrid scorer → final ranked list
  3. Compute Precision@10, Recall@10, NDCG, MRR
  4. Store results in evaluation_runs + evaluation_queries tables
  5. Print comparison against previous run (delta reporting)
```

- Evaluation runs are triggered manually or as a CI job after any change to the AI pipeline
- Results are human-readable (printed to stdout) and stored in the database for trend analysis
- No user data is exposed during evaluation — evaluation uses a test partition of the dataset

---

## 13. Notifications

### Design

Notifications are first-class entities stored in the `notifications` table. They are delivered in two channels:

1. **In-app**: Polled or pushed via WebSocket to update a notification badge and dropdown
2. **Email** (post-MVP): Triggered asynchronously via a task queue

**Notification Types**

| Type                           | Trigger                                        | Recipient         |
| ------------------------------ | ---------------------------------------------- | ----------------- |
| `match.accepted`               | Mentor accepts a student                       | Student           |
| `match.rejected`               | Mentor rejects a student                       | Student           |
| `message.received`             | New chat message sent                          | Other participant |
| `feedback.received`            | Mentor submits project feedback                | Student           |
| `resume.parsed`                | Resume parsing completes (success or failure)  | Student           |
| `project.deadline_approaching` | Project timeline within 7 days of closing      | Student (matched) |
| `project.new_candidates`       | New candidates available after profile updates | Mentor            |

---

### In-App Delivery

**Architecture**

- `NotificationService` creates a `Notification` record and optionally pushes it over the existing chat WebSocket connection if the recipient is online
- If the recipient is offline, the notification is stored and fetched on next login via `GET /api/notifications`

**Endpoints**

- `GET /api/notifications` — paginated list of notifications for the current user (unread first)
- `POST /api/notifications/{id}/read` — marks a single notification as read
- `POST /api/notifications/read-all` — marks all notifications as read

---

### Implementation Stack

- **Storage**: `notifications` table in PostgreSQL
- **Real-time delivery**: Piggybacks on FastAPI WebSocket connections (same connection used for chat); notifications are pushed as a JSON message with `type: "notification"`
- **Background triggers**: Notification creation is called from service methods (e.g., `MatchService.accept()` calls `NotificationService.create(type="match.accepted", ...)`)
- **Email (post-MVP)**: Celery + Redis task queue sends emails asynchronously

---

## 14. Chat (Realtime)

### FastAPI WebSockets

**Why Selected**

- Native to FastAPI — no additional infrastructure or library required
- Sufficient for MVP-scale real-time chat (matched student ↔ mentor pairs)
- The same WebSocket connection can carry both chat messages and real-time notification pushes

**Alternatives Considered**

- _Socket.IO_: Richer feature set but Node.js-native; adds cross-language complexity
- _Ably / Pusher_: Managed WebSocket services — excellent scalability but cost and external dependency

**Trade-offs**

- FastAPI WebSockets do not natively support horizontal scaling (sticky sessions needed with a load balancer)
- Message persistence requires explicit database writes on every message

**Architecture**

- Each active chat session is a WebSocket connection routed to the backend
- Messages and notifications are persisted to PostgreSQL on receipt
- Connection state is managed in-memory; Redis pub/sub will be added when multi-instance deployment is needed

**Future Replacement Strategy**
Add Redis pub/sub as a message bus between WebSocket server instances when horizontal scaling is required.

---

## 15. Deployment

### Frontend: Vercel (Static SPA)

**Why Selected**

- Vercel deploys Vite static bundles with zero configuration — point to the `dist/` output folder
- Global CDN edge network for fast asset delivery
- Preview deployments on every pull request
- No Next.js lock-in — the static bundle is portable to any CDN

**Trade-offs**

- Client-side routing requires a `vercel.json` rewrite rule

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

---

### Backend: Railway

**Why Selected**

- Simple container deployment from a `Dockerfile`
- Automatic HTTPS, custom domains, and environment variable management
- No Kubernetes overhead at MVP scale

**Trade-offs**

- Railway costs scale linearly with compute

---

### Database: Supabase (PostgreSQL + pgvector)

**Why Selected**

- Managed PostgreSQL with pgvector pre-installed
- Backup management and connection pooling (PgBouncer) included
- FastAPI connects via standard `asyncpg` driver — no Supabase SDK required

**Note**: Supabase is used as a managed PostgreSQL host only. Supabase Auth, Supabase Storage, and Supabase Realtime are not used.

**Future Replacement Strategy**
Migrate to a dedicated PostgreSQL instance (Railway-managed or AWS RDS) if Supabase limits are reached.

---

## 16. Development Tools

| Tool                        | Purpose                                                                      |
| --------------------------- | ---------------------------------------------------------------------------- |
| **pip & venv**              | Python dependency management and virtual environments                        |
| **npm**                     | Node.js package manager for the frontend                                     |
| **Vite**                    | Frontend build tool and dev server (`vite.config.ts`)                        |
| **React Router v6**         | Client-side routing for the SPA                                              |
| **Alembic**                 | Database schema migrations for SQLAlchemy                                    |
| **SQLAlchemy 2.0**          | Python ORM with async support (`asyncpg`)                                    |
| **Pydantic v2**             | Request/response schema validation throughout the backend                    |
| **Ruff**                    | Extremely fast Python linter and formatter (replaces Black + Flake8 + isort) |
| **ESLint + Prettier**       | TypeScript/JSX linting and formatting                                        |
| **pytest + pytest-asyncio** | Python unit and integration testing with async support                       |
| **Vitest**                  | Fast TypeScript/React unit testing (Vite-native)                             |
| **Playwright**              | End-to-end browser testing                                                   |
| **Docker + Docker Compose** | Local development environment (database, Ollama, backend)                    |
| **GitHub Actions**          | CI/CD pipeline: lint, test, build, deploy                                    |
| **Pre-commit hooks**        | Enforce lint and format on every commit                                      |

---

## 17. Project Structure

```
projectmatchai/
├── frontend/                    # Vite + React SPA
│   ├── index.html               # SPA entry point
│   ├── vite.config.ts
│   ├── vercel.json              # SPA rewrite rule
│   └── src/
│       ├── main.tsx             # React app entry point
│       ├── App.tsx              # Root component + React Router routes
│       ├── pages/               # Route-level page components
│       │   ├── auth/            # Login, Register pages
│       │   ├── student/         # Dashboard, profile, roadmap, reports
│       │   ├── mentor/          # Dashboard, project management, candidates
│       │   └── admin/           # Admin stats + user/project management
│       ├── components/
│       │   ├── ui/              # shadcn/ui base components
│       │   └── features/        # Feature-specific components (by domain)
│       │       ├── auth/
│       │       ├── profile/
│       │       ├── matching/
│       │       ├── chat/
│       │       ├── notifications/
│       │       └── ...
│       ├── context/
│       │   └── AuthContext.tsx  # Auth state (user, login, logout, isLoading)
│       ├── hooks/               # Custom React hooks
│       ├── lib/
│       │   └── api/             # Typed fetch wrappers per feature
│       ├── router/
│       │   └── ProtectedRoute.tsx
│       └── types/               # Shared TypeScript types
│
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── main.py              # Application entry point + startup lifecycle
│   │   ├── config.py            # Pydantic BaseSettings
│   │   ├── dependencies.py      # FastAPI Depends() functions
│   │   ├── database.py          # SQLAlchemy async engine + session factory
│   │   └── features/            # Feature modules (by domain)
│   │       ├── auth/
│   │       │   ├── router.py    # FastAPI router
│   │       │   ├── service.py   # Business logic
│   │       │   ├── repository.py
│   │       │   ├── schemas.py   # Pydantic request/response schemas
│   │       │   └── models.py    # SQLAlchemy ORM models
│   │       ├── profile/
│   │       ├── projects/
│   │       ├── matching/
│   │       ├── notifications/
│   │       ├── chat/
│   │       ├── feedback/
│   │       └── admin/
│   │
│   ├── ai/                      # AI service layer (framework-agnostic)
│   │   ├── providers/
│   │   │   ├── base.py          # Abstract LLMProvider
│   │   │   ├── groq.py          # Development + cloud staging
│   │   │   └── ollama.py        # Self-hosted production
│   │   ├── embeddings/
│   │   │   ├── base.py          # Abstract EmbeddingService
│   │   │   └── bge.py           # BAAI/BGE-M3 via sentence-transformers
│   │   ├── reranking/
│   │   │   └── bge_reranker.py  # BGE Reranker v2
│   │   ├── generation/          # Centralised LLM text generation
│   │   │   ├── base.py          # GenerationService base class
│   │   │   ├── explanation.py   # ExplanationGenerator
│   │   │   ├── roadmap.py       # RoadmapGenerator
│   │   │   ├── ats.py           # ATSGenerator
│   │   │   ├── readiness.py     # ReadinessGenerator
│   │   │   └── prompts/         # Plain-text prompt templates
│   │   │       ├── explanation.txt
│   │   │       ├── roadmap.txt
│   │   │       ├── ats.txt
│   │   │       └── readiness.txt
│   │   ├── parsing/
│   │   │   ├── pdf_parser.py    # PyMuPDF
│   │   │   └── ocr_parser.py    # PaddleOCR (fallback)
│   │   ├── matching/
│   │   │   └── hybrid_scorer.py
│   │   └── evaluation/
│   │       ├── dataset.py       # Load evaluation dataset
│   │       ├── metrics.py       # Precision@K, Recall@K, NDCG, MRR
│   │       └── runner.py        # Orchestrates evaluation run + stores results
│   │
│   ├── alembic/                 # Database migrations
│   └── tests/
│       ├── unit/
│       └── integration/
│
├── specs/                       # Project constitution
│   ├── 00-principles.md         # Engineering principles (How we build)
│   ├── mission.md               # Product mission (What we build)
│   ├── tech-stack.md            # Technology decisions
│   ├── roadmap.md               # Phased implementation plan
│   ├── templates/               # Templates — use before starting any feature
│   │   ├── feature-template.md
│   │   ├── adr-template.md
│   │   ├── api-template.md
│   │   └── validation-template.md
│   ├── adrs/                    # Architecture Decision Records
│   └── features/                # Per-feature specification documents
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 18. Coding Standards

### Python (Backend)

- **Formatter/Linter**: Ruff (replaces Black, isort, Flake8)
- **Type hints**: Required on all function signatures and class attributes
- **Docstrings**: Google-style docstrings on all public functions and classes
- **Async**: All I/O-bound operations (database, HTTP, file I/O) must use `async`/`await`
- **No logic in `router.py`**: Route handlers call service methods only; no business logic
- **No raw SQL in `service.py`**: All database access goes through `repository.py` using SQLAlchemy ORM
- **Pydantic schemas**: Separate `Request` and `Response` schemas; never expose ORM models directly in API responses

### TypeScript (Frontend)

- **Formatter/Linter**: ESLint + Prettier
- **Strict mode**: `"strict": true` in `tsconfig.json`
- **No `any`**: Use `unknown` and narrow types explicitly
- **Components**: Functional components only; no class components
- **Routing**: React Router v6 — all protected routes wrapped in `<ProtectedRoute role="student">` (client-side guard)
- **State management**: React Context for auth state; server state via React Query (`@tanstack/react-query`)
- **API calls**: Centralised in `src/lib/api/` with typed response schemas
- **Lazy loading**: `React.lazy` + `Suspense` for page-level code splitting

### Naming Conventions

| Context               | Convention         | Example                   |
| --------------------- | ------------------ | ------------------------- |
| Python files          | `snake_case`       | `hybrid_scorer.py`        |
| Python classes        | `PascalCase`       | `HybridScorer`            |
| Python functions/vars | `snake_case`       | `calculate_match_score()` |
| TypeScript files      | `kebab-case`       | `match-card.tsx`          |
| TypeScript components | `PascalCase`       | `MatchCard`               |
| TypeScript functions  | `camelCase`        | `fetchCandidates()`       |
| Database tables       | `snake_case`       | `student_profiles`        |
| Environment variables | `UPPER_SNAKE_CASE` | `LLM_PROVIDER`            |

---

## 19. Testing Strategy

### Philosophy

Tests are part of every phase's Definition of Done. A dedicated E2E phase validates the complete integrated system before deployment.

### Layers

| Layer             | Tool                         | Scope                                                                 |
| ----------------- | ---------------------------- | --------------------------------------------------------------------- |
| **Unit**          | pytest / Vitest              | Individual functions and components in isolation                      |
| **Integration**   | pytest + `httpx.AsyncClient` | API endpoint behaviour with a real test database                      |
| **AI Evaluation** | `ai/evaluation/runner.py`    | Offline metrics (Precision@K, NDCG, MRR) against ground-truth dataset |
| **E2E**           | Playwright                   | Full user flows from browser to database and back                     |

### Per-Phase Testing Requirements

Each phase must include:

- Unit tests for all new service and utility functions
- Integration tests for all new API endpoints
- Type checks passing (`pyright`, `tsc --noEmit`)

---

## 20. Dependency Injection

### FastAPI Native DI

FastAPI's `Depends()` system is used for all dependency injection:

```python
# dependencies.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User: ...

async def get_embedding_service() -> EmbeddingService: ...
async def get_llm_provider() -> LLMProvider: ...
```

AI service providers (LLM, embedding, reranking) are instantiated at startup and stored on `app.state`. This avoids repeated model loading on every request.

```python
# main.py
@app.on_event("startup")
async def startup():
    app.state.llm_provider = create_llm_provider(settings.LLM_PROVIDER)
    app.state.embedding_service = BGEEmbeddingService()
    app.state.reranker = BGEReranker()
```

---

## 21. Configuration Management

### Pydantic BaseSettings

All configuration is managed through a single `Settings` class:

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # AI
    LLM_PROVIDER: Literal["groq", "ollama"] = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # Embeddings
    BGE_MODEL_NAME: str = "BAAI/bge-m3"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

Secrets are never hardcoded. `.env.example` documents all required variables. `.env` is gitignored.

---

## 22. Logging

### Structured Logging (structlog)

- All backend logs are emitted as structured JSON in production
- Development mode uses human-readable coloured output
- Every request is assigned a `request_id` (UUID) propagated through all log entries via middleware
- Log levels: `DEBUG` (dev), `INFO` (production), `ERROR` (always)
- AI inference calls log: model name, latency, provider, token count

```python
log.info("match.candidates_retrieved",
    project_id=project_id,
    candidate_count=len(candidates),
    retrieval_latency_ms=latency)
```

---

## 23. Error Handling

### Backend

- All expected errors raise typed `HTTPException` subclasses with consistent `detail` structure
- Unexpected errors are caught by a global exception handler, logged with full traceback, and return a generic 500 response (no stack traces to clients)
- Validation errors (Pydantic) return 422 with field-level detail automatically
- AI inference errors are caught in service methods and surface a graceful degradation response (matching proceeds without LLM explanation if the LLM provider is unavailable)

### Frontend

- API errors are handled centrally in React Query `onError` callbacks
- User-facing error messages are plain English, not technical codes
- Network failures show a retry prompt

---

## 24. Future Scalability

| Concern                      | Current Solution                      | Future Solution                                          |
| ---------------------------- | ------------------------------------- | -------------------------------------------------------- |
| Vector search at scale       | pgvector HNSW                         | Qdrant or Weaviate dedicated cluster                     |
| LLM throughput               | Groq API (dev) / Ollama (self-hosted) | vLLM or TGI for batched inference at scale               |
| WebSocket horizontal scaling | In-memory, single instance            | Redis pub/sub message bus                                |
| Background AI jobs           | Inline async processing               | Celery + Redis task queue                                |
| Notification email delivery  | Not implemented (MVP)                 | Celery + SendGrid or SES                                 |
| Multi-tenancy                | Single schema, role-based             | Schema-per-tenant or row-level security                  |
| Embedding model upgrades     | Manual re-embed job                   | Versioned embeddings + automated re-embed pipeline       |
| CDN / file storage           | Local filesystem (dev)                | S3-compatible object storage (e.g., Cloudflare R2)       |
| OpenAI for production        | Groq (dev/staging)                    | Add `OpenAIProvider` class — zero business logic changes |
| AI evaluation automation     | Manual trigger                        | CI job on every AI pipeline change                       |

---

_This document was authored as part of the ProjectMatchAI project constitution and should be updated whenever a technology choice changes._
