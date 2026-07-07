# Feature Specification

## Feature Name

Candidate–Project Fit Report (downloadable PDF)

## Status

`[ ] Draft` | `[ ] Review` | `[ ] Approved` | `[ ] In Progress` | `[x] Done` | `[ ] Deferred`

## Author

ProjectMatchAI team

## Date

2026-07-03

## Related Phase

Phase 7 - Candidate–Project Fit Report

## Related ADRs

- `ADR-0001-standalone-bulk-intake-matching-mvp.md` (backend owns matching, scoring, and explanations; frontend is the operator surface).

---

## 1. Problem Statement

The recommendation APIs (Phase 4) and batch score matrix (Phase 5) surface ranked
matches and score breakdowns in the operator console, but an operator cannot hand a
student or mentor a single, self-contained artifact that explains _why_ a specific
candidate fits a specific project and _how_ the candidate should close their gaps.
Screenshots of the dashboard lose the qualitative reasoning and are not shareable or
archivable. Operators need a downloadable, print-ready readiness report for one
candidate–project pair, combining the deterministic factor breakdown with a candid,
actionable "how to get ready" analysis.

---

## 2. Proposed Solution

Add a single endpoint that generates a one-click PDF fit report for a
candidate–project pair. The report reuses the existing full scoring path to obtain the
deterministic factor breakdown (topic match, required skills, relevant experience,
GitHub profile, coding profiles, achievements), then asks the LLM for a structured
readiness analysis (fit summary, in-depth assessment, strengths, gaps, improvement
plan, learning roadmap, recommended resources, how-to-approach steps, mentor risks).
Both are rendered to print-safe HTML and printed to PDF in-process using PyMuPDF's
Story engine — a dependency already present for resume parsing, so no new libraries.
The operator triggers the download from a candidate's recommendation card in the
dashboard.

---

## 3. User Stories

- As an **operator**, I want to download a PDF fit report for a candidate–project pair, so that I can share a self-contained readiness assessment with the student or mentor.
- As a **student** (via the operator), I want to see concrete strengths, gaps, a learning roadmap, and how to start contributing, so that I know how to become ready for the project.
- As a **mentor** (via the operator), I want a candid list of risks and watch-outs plus the deterministic factor breakdown, so that I can make an informed take-on decision.

---

## 4. Input and Output Contracts

### Inputs

| Input                 | Required | Contract                                                                          |
| --------------------- | -------- | --------------------------------------------------------------------------------- |
| `registration_number` | Yes      | Query param. Must match an existing `candidates.registration_number`; else `404`. |
| `project_id`          | Yes      | Query param, integer. Must match an existing `projects.id`; else `404`.           |

### Outputs

| Output    | Consumer         | Contract                                                                                                            |
| --------- | ---------------- | ------------------------------------------------------------------------------------------------------------------- |
| PDF bytes | Operator browser | `application/pdf`, `Content-Disposition: attachment; filename="fit-report-{registration_number}-{project_id}.pdf"`. |

---

## 5. Scope

### In Scope

- `GET /api/matching/report` returning a PDF for one candidate–project pair.
- Deterministic factor breakdown reused from the existing scoring path (scoring v3.1.0).
- LLM-generated structured readiness analysis with a deterministic fallback skeleton.
- In-process HTML→PDF rendering via PyMuPDF's Story engine (off the event loop thread).
- Frontend download action on the recommendation card.

### Out of Scope

- Batch/cohort report generation (one pair per request only).
- Persisting generated PDFs or the analysis to disk or the database (computed on the fly, in-memory).
- Mentor-perspective report variant (the report is written for candidate readiness; mentor risks are one section, not a separate document).
- Custom branding/templating beyond the fixed inline-styled layout.

---

## 6. Solution Options and Trade-offs

### Option 1: MVP Approach

Client-side rendering — return the analysis + factors as JSON and let the browser build a PDF (e.g. `window.print()` of a hidden route).

| Dimension            | Assessment                                           |
| -------------------- | ---------------------------------------------------- |
| Complexity           | Low backend, but scatters layout logic into the SPA. |
| Development effort   | Medium (print CSS, hidden route, browser quirks).    |
| Maintainability      | Poor — output depends on the operator's browser.     |
| Scalability          | N/A (client does the work).                          |
| Performance          | Fast, but inconsistent output.                       |
| Cost                 | None.                                                |
| Future extensibility | Weak — no server-side archival path.                 |

### Option 2: Recommended Production Approach

Server-side, in-process PDF via PyMuPDF's Story engine. Backend assembles the same factor breakdown used everywhere else, adds one LLM analysis call, renders print-safe HTML to PDF off-thread, and streams the bytes.

| Dimension            | Assessment                                                                      |
| -------------------- | ------------------------------------------------------------------------------- |
| Complexity           | Moderate; contained in `report.py` + one service method.                        |
| Development effort   | Moderate; no new dependency (PyMuPDF already used for resumes).                 |
| Maintainability      | Good — single source of truth for factors; deterministic layout.                |
| Scalability          | Good enough for per-pair, on-demand generation; render runs on a worker thread. |
| Performance          | Dominated by the LLM call (~15–40s); PDF render is sub-second.                  |
| Cost                 | One LLM completion per report.                                                  |
| Future extensibility | Strong — server can later persist/email reports.                                |

### Option 3: Enterprise Approach

Dedicated document service (headless Chromium / WeasyPrint) with templating, queuing, and object-storage archival.

| Dimension            | Assessment                                      |
| -------------------- | ----------------------------------------------- |
| Complexity           | High; new service, new dependencies, new infra. |
| Development effort   | High.                                           |
| Maintainability      | Good long-term, heavy short-term.               |
| Scalability          | Excellent.                                      |
| Performance          | Good with a worker pool.                        |
| Cost                 | New infra + heavier deps.                       |
| Future extensibility | Excellent.                                      |

### Recommendation

**Option 2.** It keeps the deterministic factor breakdown consistent with the rest of
matching, adds no new dependency, and renders reliably server-side. Option 1 sacrifices
output consistency and archival; Option 3 is disproportionate for an on-demand,
per-pair MVP report and violates the "no new dependencies without approval" constraint.

---

## 7. Industry Practice

Startups typically ship client-side `print()` or a hosted PDF SaaS. Mid-sized SaaS
companies standardize on a server-side HTML→PDF renderer (WeasyPrint / headless
Chromium) behind a small service. Large companies run a dedicated document/render
service with templating and archival. This feature deliberately takes the mid-sized
shape but reuses the already-bundled PyMuPDF engine instead of adding a renderer,
matching the MVP's "no new deps" and backend-boundary-first principles.

---

## 8. API Design

| Method | Path                   | Description                                                        | Auth Required | Caller/Role |
| ------ | ---------------------- | ------------------------------------------------------------------ | ------------- | ----------- |
| `GET`  | `/api/matching/report` | Generate and stream a PDF fit report for a candidate–project pair. | No (MVP)      | `operator`  |

Errors: `404` when the candidate or project is not found; `503` when the LLM is not
configured/ready (`MatchingUnavailableError`) or the PDF fails to render
(`ReportRenderError`).

Full endpoint detail: see `specs/apis/bulk-intake-and-matching-api.md`.

---

## 9. Data Model Changes

### New Tables

None. The report is computed on the fly and streamed; nothing is persisted.

### Modified Tables

None.

### Migrations

- [x] No migration required (no schema change).

---

## 10. Service Design

```python
class MatchService:
    async def build_match_report(
        self, *, registration_number: str, project_id: int
    ) -> tuple[str, bytes]:
        """Build a downloadable PDF fit report for one candidate-project pair.

        Loads the candidate (skills, documents, repo/live-app evaluations) and the
        project (mentor, prerequisites, preferences), ensures candidate metrics,
        computes the developer-profile score and pair signals, reuses the full
        scoring path to build the ranked recommendation and factor breakdown, asks
        the LLM for a structured improvement analysis, renders print-safe HTML, and
        prints it to PDF. Returns (filename, pdf_bytes).
        """
        ...
```

Supporting module `app/features/matching/report.py`:

- `generate_improvement_analysis(...) -> dict` — one LLM call returning a structured
  JSON dict (`fit_summary`, `detailed_assessment`, `strengths`, `gaps`,
  `improvement_plan`, `learning_roadmap`, `recommended_resources`, `project_approach`,
  `risks`). On any error it logs and returns a deterministic skeleton so the PDF never
  hard-fails.
- `build_report_html(context) -> str` — renders the analysis + factor breakdown into
  Story-safe HTML (tables + inline styles only; no flex/float/gradient).
- `render_html_to_pdf(html) -> bytes` — prints via `fitz.Story` on a worker thread
  (`asyncio.to_thread`); raises `ReportRenderError` on failure.

---

## 11. AI / Generation Components

| Component                      | Module                                                              | Prompt Template                                                                                                                                                                                                                          | Fallback                                                                                                                                     |
| ------------------------------ | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Readiness/improvement analysis | `matching/report.py::generate_improvement_analysis`                 | System = "technical mentor writing a candid readiness report … respond with ONLY a JSON object"; user prompt embeds project title/abstract, required skills, computed factor scores, candidate name, and truncated resume (≤9000 chars). | On any exception (parse/provider/timeout): deterministic skeleton with empty narrative sections; the PDF still renders the factor breakdown. |
| Pair evaluation (reused)       | `matching/match_explanation.py::generate_project_match_for_student` | Existing student-perspective evaluation prompt.                                                                                                                                                                                          | Existing deterministic score fallback.                                                                                                       |

Rules honored:

- LLM calls go through `matching/llm_client.generate_chat_completion` (the feature's
  generation boundary); no ad-hoc provider calls in the router/service.
- Generated text is grounded in the resume and the computed factor scores.
- Provider failure has a tested-in-practice fallback (deterministic skeleton).

**Known limitation:** the analysis call has no retry (unlike the evaluation path's
2-attempt retry). A single transient LLM failure (429/timeout) silently degrades the
report to the empty skeleton while still returning `200`. See `validation.md` and Open
Questions.

---

## 12. Frontend Components

### New Pages

None.

### New Components

| Component  | File | Props                                                  |
| ---------- | ---- | ------------------------------------------------------ |
| (none new) | —    | Download wired into the existing `RecommendationCard`. |

### New API Client

| Function                                             | File                             | Purpose                                                                                             |
| ---------------------------------------------------- | -------------------------------- | --------------------------------------------------------------------------------------------------- |
| `downloadMatchReport(registrationNumber, projectId)` | `frontend/src/lib/api/report.ts` | `GET /matching/report` as a blob, then triggers a browser download of `fit-report-{reg}-{pid}.pdf`. |

`RecommendationCard.tsx` gains a "download report" action that calls
`downloadMatchReport` and surfaces a readable error on failure.

---

## 13. Validation and Test Plan

| Test Type   | What Is Tested                                      | Expected Outcome                                                |
| ----------- | --------------------------------------------------- | --------------------------------------------------------------- |
| Integration | `GET /api/matching/report` with a valid pair        | `200`, `application/pdf`, non-empty body starting with `%PDF-`. |
| Integration | Unknown `registration_number` or `project_id`       | `404`.                                                          |
| Integration | LLM not configured                                  | `503`.                                                          |
| Unit        | `build_report_html` with a populated analysis       | Contains every section heading and escapes user text.           |
| Unit        | `generate_improvement_analysis` when the LLM raises | Returns the deterministic skeleton (no exception).              |

See `validation.md` for the full plan. **Current state:** the endpoint and rendering
are verified manually end-to-end (a 3-page PDF for `MDS202537` × project 6); automated
tests for this feature are not yet written (tracked as a gap).

---

## 14. Definition of Done

- [x] Architecture approved (reuses ADR-0001; no new dependency).
- [x] Endpoint returns correct status codes and a PDF body.
- [ ] Service method has unit tests. _(gap — not yet written)_
- [ ] Endpoint has an integration test. _(gap — not yet written)_
- [x] AI fallback behavior exists (deterministic skeleton).
- [x] No Alembic migration required.
- [x] FastAPI OpenAPI docs expose the endpoint.
- [ ] README / `.env.example` updated if setup changed. _(no new env vars)_
- [x] Ruff (backend) and ESLint (frontend) pass.
- [x] No `any` types in new TypeScript.
- [x] No raw SQL in service/router layers.
- [x] No LLM calls outside the matching generation boundary.

---

## 15. Open Questions

| Question                                                                                                        | Owner    | Resolution Date | Decision                                                                                  |
| --------------------------------------------------------------------------------------------------------------- | -------- | --------------- | ----------------------------------------------------------------------------------------- |
| Should the analysis call retry on transient LLM failure instead of silently falling back to the empty skeleton? | matching | Open            | Proposed: add backoff retry (mirror the eval path) or return `503` so the caller retries. |
| Should generated reports be persisted/emailable?                                                                | product  | Open            | Deferred to Post-MVP.                                                                     |

---

_Feature Template version 2.0 - ProjectMatchAI_
