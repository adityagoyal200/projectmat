# Phase 7 - Candidate–Project Fit Report - Implementation Plan

## 1. Report module (`app/features/matching/report.py`)

1. **LLM analysis** — `generate_improvement_analysis(...)`: build a mentor-style prompt embedding project title/abstract, required skills, the computed factor summary, and the truncated resume (≤9000 chars); request a strict JSON object with keys `fit_summary`, `detailed_assessment`, `strengths`, `gaps`, `improvement_plan`, `learning_roadmap`, `recommended_resources`, `project_approach`, `risks`. Strip code fences, slice to the outermost `{...}`, and normalize each list field. On any exception, log `report.analysis_failed` and return a deterministic skeleton (empty sections) so rendering never hard-fails.
2. **HTML assembly** — `build_report_html(context)`: render header (candidate name, project title, big MATCH score), the fit-summary callout, each narrative section, and the factor-breakdown table. Use tables + inline styles only (no flex/float/gradient) so PyMuPDF's Story engine lays it out faithfully; HTML-escape all user-derived text; color scores by strength (`_score_color`: green ≥70, amber ≥45, red below).
3. **PDF render** — `render_html_to_pdf(html)`: drive `fitz.Story` + `fitz.DocumentWriter` over A4 pages on a worker thread via `asyncio.to_thread`; raise `ReportRenderError` on failure.

## 2. Service method (`app/features/matching/service.py`)

1. `MatchService.build_match_report(*, registration_number, project_id)`:
   - `_ensure_llm_ready()`; load the candidate (skills, documents, repository/live-app evaluations) and project (mentor, prerequisites, preferences); `404` (raise `ValueError`) when either is missing.
   - Merge workbook + resume-extracted skills; ensure candidate metrics (`_ensure_candidate_metrics`, commit if changed).
   - Compute `compute_developer_profile_score(...)` and `_compute_pair_signals(...)`.
   - Reuse `generate_project_match_for_student(...)` for the qualitative evaluation (best-effort; tolerate failure).
   - Build the ranked recommendation via `_build_project_recommendation(...)`; derive the factor breakdown via `_report_factors(rec)` and a compact `factor_summary` string.
   - Call `generate_improvement_analysis(...)`; assemble the context and call `build_report_html` → `render_html_to_pdf`.
   - Return `(f"fit-report-{registration_number}-{project_id}.pdf", pdf_bytes)`.
2. `_report_factors(rec)`: map score components/breakdown to labeled rows (Topic match, Required skills, Relevant experience, GitHub profile, Coding profiles, Achievements) each with a plain-language `meaning` and the deterministic `detail` string.

## 3. Router (`app/features/matching/router.py`)

1. `GET /api/matching/report` — read `registration_number` + `project_id`; call `service.build_match_report`; return a `Response` with `media_type="application/pdf"` and a `Content-Disposition: attachment` header.
2. Map errors: `MatchingUnavailableError` → `503`, `ValueError` (not found) → `404`, `ReportRenderError` → `503`.

## 4. Frontend (`frontend/src/`)

1. `lib/api/report.ts` — `downloadMatchReport(registrationNumber, projectId)`: `GET /matching/report` with `responseType: 'blob'`, wrap in a `Blob`, and trigger an anchor download named `fit-report-{reg}-{pid}.pdf`; throw a readable error on failure.
2. `components/dashboard/RecommendationCard.tsx` — add a download action wired to `downloadMatchReport`, with loading/disabled state and a surfaced error message.

## 5. Tests (gap — planned, not yet implemented)

1. Unit: `build_report_html` includes every section and escapes user text; `generate_improvement_analysis` returns the skeleton (no raise) when the LLM errors.
2. Integration: `GET /api/matching/report` returns `200` + `application/pdf` for a valid pair; `404` for unknown ids; `503` when the LLM is unconfigured.
