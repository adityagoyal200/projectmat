# Feature Specification: Project Setup

> **Related Phase**: Phase 0 - Project Setup
> **Status**: `[ ] Done` > **Author**: Senior Software Engineer
> **Date**: 2026-06-26

---

## 1. Problem Statement

Before any functional features (like authentication, profile parsing, or project matching) can be implemented, the project needs a solid, clean, and unified foundation. Developers and automated coding agents need a consistent development environment, clear coding standards, and pre-configured tooling. Without a shared workspace containing pre-commit hooks, linting rules, structured logging, a dockerized database, and basic scaffolding, implementation risks inconsistent architectures, dependency conflicts, and slower velocity.

---

## 2. Goals

- **G1**: Establish a unified monorepo structure containing frontend, backend, database configuration, and documentation.
- **G2**: Spin up local development infrastructure (PostgreSQL + pgvector and Ollama) using Docker Compose.
- **G3**: Create a runnable FastAPI backend with configuration management, structured logging, error handling, and a database-aware health check.
- **G4**: Scaffold a Vite + React + TypeScript frontend with Tailwind CSS, shadcn/ui, routing, and HTTP client utility.
- **G5**: Enforce quality gates through local pre-commit hooks and a CI pipeline (GitHub Actions) for linting and type-checking.

---

## 3. User Stories

- As a **Developer**, I want to run a single command to start the database and Ollama, so that I can begin local development immediately.
- As a **Developer**, I want my code formatted and linted automatically before committing, so that we maintain high code standards across the repo.
- As an **API Consumer**, I want a health check endpoint `/api/health` that checks database connectivity, so that deployment platforms can monitor app readiness.
- As a **Frontend Developer**, I want styled UI component structures and routing set up, so that I can construct user interfaces without configuring boilerplate.

---

## 4. Scope

### In Scope

- **Repository and Tooling**: Monorepo layout (`/frontend`, `/backend`, `/specs`), `.gitignore`, `.env.example`, README setup instructions.
- **Backend Infrastructure**: Uvicorn + FastAPI scaffolding, pip requirements.txt dependency management, Pydantic `Settings`, Structlog logging (JSON in production, colorized in dev), custom exception handlers.
- **Database Engine Connectivity**: SQLAlchemy 2.0 async engine via `asyncpg` connecting to Docker PostgreSQL. Alembic initialized.
- **Health Check Endpoint**: `GET /api/health` checking database query performance and status.
- **Frontend Infrastructure**: Vite + React 18 (TypeScript), Tailwind CSS v3, React Router v6, shadcn/ui base installation with `Button`, `Input`, `Card`.
- **API Client**: `src/lib/api/client.ts` with Axios or native `fetch` client proxying request to backend, handling auth headers and base configurations.
- **CI / Quality Checks**: Pre-commit hooks configuration (Ruff, Pyright, Prettier, ESLint). GitHub Actions CI workflow running Ruff/Pyright on push/pull request.
- **Development Routing / CORS**: Backend CORS middleware and frontend Vite dev proxy configured.

### Out of Scope (Explicitly Deferred)

- **Database Schemas & Migrations**: Relational tables, model definitions, and SQLAlchemy schemas are deferred to Phase 1.
- **Authentication Forms & Endpoints**: Standalone student/mentor auth is deferred. MVP integration auth will be specified when the bulk intake API is implemented.
- **AI Integrations & Generation Services**: Embedding, parsing, and LLM provider logic are deferred to the bulk intake and matching phases.

---

## 5. API Design

The following endpoint is introduced in this phase to verify workspace integration:

| Method | Path          | Description                                            | Auth Required | Role      |
| ------ | ------------- | ------------------------------------------------------ | ------------- | --------- |
| `GET`  | `/api/health` | Checks backend system health and database connectivity | No            | Anonymous |

### Expected Health Response

```json
{
  "status": "ok",
  "database": "connected",
  "environment": "development",
  "timestamp": "2026-06-26T12:00:00Z"
}
```

---

## 6. Technical Decisions

### Monorepo Structure

- Backend and Frontend reside in `/backend` and `/frontend` directories. Shared specs reside in `/specs`.
- Allows single-repository management with isolated dependency environments.

### Development Environment & Proxy

- Vite configures a development proxy mapping `/api` requests to backend (`http://localhost:8000`).
- Backend enables `CORSMiddleware` to allow explicit cross-origin resource sharing from the local frontend origin.

### Package Management

- Backend uses **pip** for dependency tracking and standard virtual environments (`venv`).
- Frontend uses **npm** as the Node package manager (consistent with team conventions).

### Databases & Extensions

- **PostgreSQL 15+** with the **pgvector** extension.
- Spin up using Docker Compose for local environments.
- Connection is managed asynchronously via SQLAlchemy 2.0 and the `asyncpg` driver.

### Structured Logging

- Configured using **structlog**. Every request logs an injected `request_id` (via middleware) to trace execution flow across handlers.

---

## 7. Dependencies

- **Docker Desktop** installed on development systems.
- **Python 3.11+** configured on system path.
- **Node.js 18+** and **npm** installed.

---

## 8. Risks

- **VRAM Contention**: Running local Ollama models on lower-spec hardware (e.g. 4GB GPUs) could cause memory limits to exceed if models are kept active.
  - _Mitigation_: Configure Groq API key in `.env` for development LLM calls, keeping local Ollama optional.
- **Docker Port Conflicts**: Default PostgreSQL port (5432) could conflict with system-installed instances.
  - _Mitigation_: Bind the host port to a customizable variable (e.g., `POSTGRES_PORT` in `.env`) fallback.

---

## 9. Open Questions

- None. All initial requirements and architectural guidelines from the Project Constitution documents have been resolved.

---

## 10. Definition of Done

- [ ] Backend runs via standard virtual environment without error, connected to Docker PostgreSQL.
- [ ] Frontend compiles with no TypeScript or ESLint errors.
- [ ] Pre-commit hooks (Ruff, ESLint, Prettier, Pyright) succeed on files.
- [ ] `GET /api/health` returns status `"ok"` and validates DB connection.
- [ ] CI pipeline configuration `.github/workflows/ci.yml` is present.
