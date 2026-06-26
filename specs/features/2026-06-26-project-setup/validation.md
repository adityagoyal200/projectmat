# Validation & Test Plan: Project Setup

**Phase**: Phase 0 — Project Setup
**Related Feature Spec**: [specs/features/2026-06-26-project-setup/requirements.md](requirements.md)
**Author**: Senior Software Engineer
**Date**: 2026-06-26

---

## 1. Acceptance Criteria

- **AC-1**: Docker compose starts PostgreSQL (with pgvector) and Ollama services without failures.
- **AC-2**: FastAPI backend application starts successfully and binds to host port `8000`.
- **AC-3**: `GET /api/health` returns HTTP status `200` with the payload `"status": "ok"` and `"database": "connected"` when database is online.
- **AC-4**: `GET /api/health` returns HTTP status `503 Service Unavailable` with database detail `"disconnected"` if connection cannot be established.
- **AC-5**: Vite React frontend starts successfully on local port, displays landing page with shadcn UI elements, and routes requests correctly.
- **AC-6**: Git pre-commit hooks intercept commits if Ruff lints or ESLint rules fail.
- **AC-7**: GitHub Actions workflow builds the frontend, installs dependencies, and runs lints with zero errors.

---

## 2. Test Inventory

### Unit Tests

| #   | Test File                             | Function / Class Under Test | Scenario                                   | Expected Outcome                                               |
| --- | ------------------------------------- | --------------------------- | ------------------------------------------ | -------------------------------------------------------------- |
| U1  | `tests/unit/test_config.py`           | `Settings`                  | Load settings from valid `.env`            | Instantiates settings successfully                             |
| U2  | `tests/unit/test_config.py`           | `Settings`                  | Load settings with missing required fields | Raises `ValidationError`                                       |
| U3  | `tests/unit/test_logging.py`          | Logging Middleware          | Logging API calls                          | Propagates `request_id` context to log outputs                 |
| U4  | `frontend/src/lib/api/client.test.ts` | API Client                  | Parse non-200 API response                 | Triggers centralized error callback with human-readable detail |

---

### Integration Tests

| #   | Test File                          | Endpoint                | Scenario                             | Auth | Expected Status | Expected Response                                              |
| --- | ---------------------------------- | ----------------------- | ------------------------------------ | ---- | --------------- | -------------------------------------------------------------- |
| I1  | `tests/integration/test_health.py` | `GET /api/health`       | Normal conditions (DB running)       | ❌   | `200`           | `{ "status": "ok", "database": "connected" }`                  |
| I2  | `tests/integration/test_health.py` | `GET /api/health`       | Database service offline/unreachable | ❌   | `503`           | `{ "status": "error", "database": "disconnected" }`            |
| I3  | `tests/integration/test_errors.py` | `GET /api/simulate-500` | Endpoint raises unexpected Exception | ❌   | `500`           | `{ "detail": "Internal Server Error" }` (trace details hidden) |

---

### Frontend Tests

| #   | Test File                    | Component / Hook | Scenario                      | Expected Outcome                                            |
| --- | ---------------------------- | ---------------- | ----------------------------- | ----------------------------------------------------------- |
| F1  | `src/App.test.tsx`           | `App`            | Render landing page component | Landing page heading and basic shadcn/ui components display |
| F2  | `src/router/routes.test.tsx` | React Router     | Access undefined routing path | Correctly redirects to default index page                   |

---

### Security Checks

| #   | Scenario                          | Verification Method                                                        | Expected Outcome                                                                    |
| --- | --------------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| S1  | Verify CORS on API requests       | Send `OPTIONS` query to `/api/health` with `Origin: http://localhost:5173` | Headers return `Access-Control-Allow-Origin: http://localhost:5173`                 |
| S2  | Validate Error Detail Obfuscation | Query simulated 500 endpoint in production settings                        | Error response payload contains only user-safe generic info, logs capture traceback |
| S3  | Rate Limiting configuration check | Query health check endpoint 100 times in 10 seconds                        | Under default settings, returns `429 Too Many Requests` (if slowapi rule matches)   |

---

### Performance Checks

| #   | Metric                       | Scenario / Tool                                | Target SLA                                      |
| --- | ---------------------------- | ---------------------------------------------- | ----------------------------------------------- |
| P1  | Health endpoint latency      | Query health check endpoint with database ping | `< 50ms` response time                          |
| P2  | Frontend initial load        | Page load using Lighthouse or Chrome DevTools  | `< 1.5s` Largest Contentful Paint (LCP) locally |
| P3  | Development build hot reload | Vite Hot Module Replacement (HMR) latency      | `< 100ms` update reflection                     |

---

### Edge Cases & Boundary Conditions

| #   | Edge Case                                        | Expected Behaviour                                                                    |
| --- | ------------------------------------------------ | ------------------------------------------------------------------------------------- |
| E1  | Database server restarts during backend runtime  | SQLAlchemy pools rebuild connection, health endpoint recovers automatically           |
| E2  | Client sends query with unsupported HTTP headers | API request is parsed cleanly; `request_id` middleware fallback assigns new random ID |
| E3  | Vite development server restarts                 | Proxy configurations reconnect instantly on frontend reload                           |

---

## 3. Definition of Done - Tests

### Backend Quality Gates

- [ ] Pytest suite executes and passes: `pytest tests/`
- [ ] Pytest coverage report shows 100% logic coverage on config and logging utilities.
- [ ] Ruff formatting and check runs with zero warnings or errors.
- [ ] Pyright type checker passes with zero errors on all files in `/backend/app`.

### Frontend Quality Gates

- [ ] Vite client builds successfully: `npm run build`
- [ ] ESLint checks pass with no warnings.
- [ ] Prettier formatting is applied.
- [ ] TypeScript compiler runs cleanly: `tsc --noEmit`

---

## 4. Test Data Requirements

- No mock database entities or vector embeddings are needed for Phase 0 checks.
- A functional Docker instance containing PostgreSQL must be active during testing.

---

## 5. Manual Verification Steps

1. Start all docker compose containers: `docker compose up -d`
2. Run database health ping from bash: `docker exec -it projectmatchai-db pg_isready`
3. Launch backend application: `uvicorn app.main:app --reload`
4. Query the health check endpoint using curl:
   ```bash
   curl -i http://localhost:8000/api/health
   ```
   _Verify response code `200` and `"database": "connected"` JSON._
5. Launch frontend dev server: `npm run dev`
6. Open browser at `http://localhost:5173`.
   _Verify landing page styling renders and layout elements appear correctly._
7. Trigger pre-commit verification manually:
   ```bash
   pre-commit run --all-files
   ```
   _Verify all hook tests report success._

---

## 6. Merge Checklist

- [ ] All code conforms to Project Constitution principles and tech stack specs.
- [ ] CI pipeline (GitHub Actions) runs and passes cleanly.
- [ ] Local pre-commit hooks pass without warnings or warnings are resolved.
- [ ] No production source files modified; only planning files and setup configuration created.
- [ ] Peer review completed and approved.
