# ProjectMatchAI

ProjectMatchAI is an AI-powered student-mentor matching platform that matches students to projects based on growth potential rather than just pre-existing skills, incorporating explainable AI candidate ranking, automated resume parsing, interactive learning roadmaps, and realtime chat.

---

## Repository Structure

```
projectmatchai/
├── backend/                    # FastAPI application
├── frontend/                   # Vite + React SPA (TypeScript)
├── specs/                      # Project constitution and specifications
└── docker-compose.yml          # Local Postgres + pgvector & Ollama
```

---

## Local Development Setup

### Prerequisites

- **Docker Desktop**
- **Python 3.11+** and **Poetry**
- **Node.js 18+** and **npm**

---

### Step 1: Start Infrastructure Containers

Launch local PostgreSQL (with `pgvector`) and Ollama services:

```bash
docker compose up -d
```

Verify the database is online:

```bash
docker exec -it projectmatchai-db pg_isready
```

---

### Step 2: Configure Environment Variables

Copy the template environment file:

```bash
cp .env.example .env
```

Update any required API keys or port settings in the newly created `.env` file.

---

### Step 3: Backend Setup & Running

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install virtual environment and packages using Poetry:
   ```bash
   poetry install
   ```
3. Run migrations (applied in Phase 1):
   ```bash
   poetry run alembic upgrade head
   ```
4. Start the FastAPI development server:
   ```bash
   poetry run uvicorn app.main:app --reload --port 8000
   ```
   _The API docs will be available at [http://localhost:8000/docs](http://localhost:8000/docs)._

---

### Step 4: Frontend Setup & Running

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite React development client:
   ```bash
   npm run dev
   ```
   _The frontend dashboard will be available at [http://localhost:5173](http://localhost:5173)._

---

## Code Quality & Pre-commit Hooks

To enforce linting, formatting, and type-checks before commits:

1. Install pre-commit globally or in your environment:
   ```bash
   pip install pre-commit
   ```
2. Set up pre-commit hooks in the repository:
   ```bash
   pre-commit install
   ```
3. Run checks manually on all files:
   ```bash
   pre-commit run --all-files
   ```

---

## Running Tests

### Backend Tests

Execute pytest suite inside the `/backend` directory:

```bash
poetry run pytest
```

### Frontend Tests

Execute Vitest test suite inside the `/frontend` directory:

```bash
npm run test
```
