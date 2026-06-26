# Implementation Plan: Project Setup

This plan details the step-by-step actions required to establish the project skeleton and infrastructure for ProjectMatchAI.

---

## 1. Project & Monorepo Structure

- [ ] Initialize monorepo directory layout: `/backend`, `/frontend`, `/specs`.
- [ ] Create base `.gitignore` covering Python virtual environments, Node modules, system files, and local environment files.
- [ ] Create a root `.env.example` template covering configurations for database connection, ports, LLM providers, and authentication secrets.

---

## 2. Infrastructure Setup

- [ ] Configure `docker-compose.yml` defining:
  - PostgreSQL database service with `pgvector` pre-installed.
  - Ollama container service mapping volume directories for self-hosted AI models.
- [ ] Launch Docker containers and verify database availability.

---

## 3. Backend Foundation

- [ ] Initialize Poetry virtual environment and configure `pyproject.toml` dependencies.
- [ ] Install FastAPI, Uvicorn, Pydantic, SQLAlchemy, asyncpg, Alembic, structlog, and ruff.
- [ ] Scaffold the app package directory:
  - `app/main.py`: App initialization and lifecycles.
  - `app/config.py`: Environment variables management via `pydantic-settings`.
  - `app/database.py`: Async engine configuration and session provider.
  - `app/dependencies.py`: Dependency injection containers.
- [ ] Set up `structlog` configurations (JSON log format in production, colorized formatting in development).
- [ ] Write middleware to generate and inject a unique `request_id` for every API query context.

---

## 4. Database Setup

- [ ] Configure SQLAlchemy async engine and session factory to target the Docker database environment variables.
- [ ] Initialize Alembic with `alembic init alembic/` command.
- [ ] Configure `alembic.ini` and `env.py` to support asynchronous connections and read configuration variables from settings.

---

## 5. API Setup

- [ ] Define the base FastAPI app instance and configure CORS middleware with allowed origins.
- [ ] Implement the `GET /api/health` endpoint which runs a query verification against the PostgreSQL connection.
- [ ] Implement a global exception handler that logs traceback context and returns a standard error JSON response shape.

---

## 6. Frontend Setup

- [ ] Scaffold Vite project using Node/npm templates: `frontend/` containing Vite, React 18, and TypeScript.
- [ ] Install and configure Tailwind CSS v3 including post-css configurations.
- [ ] Initialize `shadcn/ui` UI library and add initial components: `Button`, `Input`, `Card`.
- [ ] Configure React Router v6 mapping default route handlers.
- [ ] Install and configure ESLint, Prettier, and TypeScript configuration rules.
- [ ] Write a base HTTP client `src/lib/api/client.ts` incorporating request interceptors for token attachment and central error parsing.
- [ ] Add `vercel.json` routing configurations to ensure single-page application redirects.

---

## 7. Testing Setup

- [ ] Set up `pytest` backend testing engine, adding basic integration test file structures and config fixtures.
- [ ] Set up Vitest frontend testing library in Vite configs.
- [ ] Configure `.pre-commit-config.yaml` to enforce Ruff lints, ESLint checks, Prettier styles, and type verification.
- [ ] Write GitHub Actions CI workflows (`.github/workflows/ci.yml`) to enforce code checks on repository updates.

---

## 8. Documentation

- [ ] Write root `README.md` containing commands for starting the Docker services, launching dev servers, running test suites, and formatting code.
- [ ] Update `roadmap.md` status checklists to track Phase 0 progress.
