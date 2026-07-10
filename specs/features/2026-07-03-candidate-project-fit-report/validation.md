# Phase 7 - Candidate–Project Fit Report - Validation Plan

## 1. Acceptance Criteria

- **AC-1**: `GET /api/matching/report?registration_number=&project_id=` returns `200` with `Content-Type: application/pdf` and a body beginning with `%PDF-` for a valid candidate–project pair.
- **AC-2**: The response sets `Content-Disposition: attachment; filename="fit-report-{registration_number}-{project_id}.pdf"`.
- **AC-3**: A fully populated report renders every section: fit summary, in-depth assessment, strengths, gaps, how-to-improve, learning roadmap, recommended resources, how-to-approach, mentor risks, and the factor breakdown.
- **AC-4**: The factor breakdown matches the deterministic scoring path (scoring v3.1.0) — same components and detail strings surfaced elsewhere in matching.
- **AC-5**: When the LLM analysis fails, the endpoint still returns a valid PDF containing the factor breakdown (deterministic skeleton), not a `500`.
- **AC-6**: Unknown `registration_number` or `project_id` returns `404`; an unconfigured LLM returns `503`.

## 2. Automated Checks (implemented 2026-07-07 — `tests/unit/test_report.py`, `tests/integration/test_matching_api.py`)

- Unit `test_build_report_html_contains_all_sections`: given a populated analysis + factors, output contains every section heading.
- Unit `test_build_report_html_escapes_user_text`: injected `<script>` / `&` in name and bullets are HTML-escaped.
- Unit `test_generate_improvement_analysis_success`: valid LLM JSON → parsed dict, one call.
- Unit `test_generate_improvement_analysis_skips_without_retry_when_disabled`: skipped result → skeleton, **no retry** (one call).
- Unit `test_generate_improvement_analysis_retries_then_succeeds`: provider error then valid → parsed dict, two calls.
- Unit `test_generate_improvement_analysis_falls_back_after_exhaustion`: always-unparseable → skeleton after `_ANALYSIS_MAX_ATTEMPTS` calls.
- Integration `test_download_match_report_candidate_not_found`: unknown registration → `404`.
- Integration `test_download_match_report_requires_llm`: LLM unavailable → `503`.
- _Deferred_: a full `200` happy-path integration test (needs the whole scoring + profile + PDF-render pipeline mocked); the `200` path is covered by the manual walkthrough below.

Commands: `cd backend && pytest tests/unit/test_report.py tests/integration/test_matching_api.py -q` (12 passing); `ruff check .`.

## 3. Manual Walkthrough (performed 2026-07-07)

1. Started stack (Postgres via Docker, backend on `:8000`, OpenAI `gpt-4o-mini`).
2. Fetched `GET /api/matching/student-recommendations/MDS202537` to pick the top real-project match (project 6, "AI powered adaptive games to resist the attention economy").
3. Called `GET /api/matching/report?registration_number=MDS202537&project_id=6` → `200`, `application/pdf`, ~116 KB, 3 pages.
4. Extracted the PDF text (PyMuPDF) and confirmed all sections present and no fallback banner.

## 4. Edge Cases

- **Transient LLM failure (observed, now mitigated)**: the analysis call originally fell back to the empty skeleton on the first attempt (rate-limit/timeout right after a 12-call recommendations run). As of 2026-07-07 the call retries up to `_ANALYSIS_MAX_ATTEMPTS` times before falling back, so a single transient failure no longer produces an empty report; the skeleton remains the terminal fallback and the endpoint still returns `200`.
- **Missing resume**: candidates without parsed resume text still produce a report driven by the factor breakdown; narrative quality degrades gracefully.
- **Long resume**: resume text is truncated to 9000 chars before the prompt to bound token cost.
- **Unicode in names/skills**: all user text is HTML-escaped before rendering.

## 5. Definition of Done

- [x] Endpoint returns a valid PDF for a real candidate–project pair (verified end-to-end).
- [x] Deterministic fallback keeps the endpoint from `500`-ing on LLM failure.
- [x] OpenAPI docs expose the endpoint.
- [x] Ruff (backend) and ESLint (frontend) clean.
- [x] Unit + integration tests written and passing (12 tests; full `200` integration test deferred).
- [x] Retry-vs-`503` decision for transient LLM failure resolved (bounded retry added; skeleton kept as terminal fallback).
