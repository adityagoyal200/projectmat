# ProjectMatchAI

ProjectMatchAI is a standalone upload-and-review app for AI-assisted student/project matching.

For the current MVP, the frontend is only the operator surface: upload inputs, review validation issues, start matching, and inspect/export results. The backend owns Excel parsing, validation, normalization, resume enrichment, matching, scoring, and explanations.

Longer term, the same backend boundary can plug into a larger program-management system.

---

## Current Scope

In scope for the next phases:

- Import candidate, mentor, and project workbooks.
- Link optional resume PDFs to candidate records.
- Validate messy rows and show actionable issues.
- Normalize students, mentors, projects, skills, and prerequisites.
- Run explicit match jobs.
- Show ranked matches by mentor/project with score breakdowns and explanations.
- Export results as JSON and XLSX.

Deferred:

- Student accounts.
- Mentor accounts.
- Chat.
- Notifications.
- Admin portal.
- Automatic final allocation.

---

## Repository Structure

```text
projectmatchai/
  backend/        FastAPI backend
  frontend/       Vite React operator console
  specs/          Product, architecture, feature, and validation specs
  docker-compose.yml
```

---

## Local Development Setup

### Prerequisites

- Docker Desktop
- Python 3.11+
- Node.js 18+ and npm

### 1. Start Infrastructure

```bash
docker compose up -d
```

Verify PostgreSQL:

```bash
docker exec -it projectmatchai-db pg_isready
```

### 2. Configure Environment

Create `.env` from `.env.example` if present, then set any local overrides needed for database or AI providers.

### 3. Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

API docs:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/api/health
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## Quality Checks

Backend:

```bash
cd backend
pytest
ruff check .
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
npm run test
```

---

## Specs

Start here before implementing any phase:

- `specs/00-principles.md`
- `specs/mission.md`
- `specs/tech-stack.md`
- `specs/roadmap.md`
- `specs/adrs/ADR-0001-standalone-bulk-intake-matching-mvp.md`
- `specs/features/2026-06-26-bulk-intake-and-matching/requirements.md`
- `specs/apis/bulk-intake-and-matching-api.md`

Architecture changes require an ADR before production code.
