# Phase 7 - Candidate–Project Fit Report - Validation Plan

## 1. Acceptance Criteria

- **AC-1**: `GET /api/matching/report?registration_number=&project_id=` returns `200` with `Content-Type: application/pdf` and a body beginning with `%PDF-` for a valid candidate–project pair.
- **AC-2**: The response sets `Content-Disposition: attachment; filename="fit-report-{registration_number}-{project_id}.pdf"`.
- **AC-3**: A fully populated report renders every section: fit summary, in-depth assessment, strengths, gaps, how-to-improve, learning roadmap, recommended resources, how-to-approach, mentor risks, and the factor breakdown.
- **AC-4**: The factor breakdown matches the deterministic scoring path (scoring v3.1.0) — same components and detail strings surfaced elsewhere in matching.
- **AC-5**: When the LLM analysis fails, the endpoint still returns a valid PDF containing the factor breakdown (deterministic skeleton), not a `500`.
- **AC-6**: Unknown `registration_number` or `project_id` returns `404`; an unconfigured LLM returns `503`.

## 2. Automated Checks (planned — not yet implemented)

- Unit `test_build_report_html_sections`: given a populated analysis + factors, output contains each section heading and HTML-escapes injected text.
- Unit `test_generate_improvement_analysis_fallback`: when `generate_chat_completion` raises, the function returns the skeleton dict (all list keys present, empty) without raising.
- Integration `test_download_match_report_ok`: valid pair → `200`, `application/pdf`, body starts with `%PDF-`.
- Integration `test_download_match_report_not_found`: unknown ids → `404`.
- Integration `test_download_match_report_llm_unavailable`: LLM disabled → `503`.

Commands: `cd backend && pytest tests/unit/... tests/integration/...`; `ruff check .`.

## 3. Manual Walkthrough (performed 2026-07-07)

1. Started stack (Postgres via Docker, backend on `:8000`, OpenAI `gpt-4o-mini`).
2. Fetched `GET /api/matching/student-recommendations/MDS202537` to pick the top real-project match (project 6, "AI powered adaptive games to resist the attention economy").
3. Called `GET /api/matching/report?registration_number=MDS202537&project_id=6` → `200`, `application/pdf`, ~116 KB, 3 pages.
4. Extracted the PDF text (PyMuPDF) and confirmed all sections present and no fallback banner.

## 4. Edge Cases

- **Transient LLM failure (observed)**: the analysis call fell back to the empty skeleton on the first attempt (rate-limit/timeout right after a 12-call recommendations run); a re-run produced the full report. The endpoint returned `200` in both cases — see the retry Open Question in `requirements.md`.
- **Missing resume**: candidates without parsed resume text still produce a report driven by the factor breakdown; narrative quality degrades gracefully.
- **Long resume**: resume text is truncated to 9000 chars before the prompt to bound token cost.
- **Unicode in names/skills**: all user text is HTML-escaped before rendering.

## 5. Definition of Done

- [x] Endpoint returns a valid PDF for a real candidate–project pair (verified end-to-end).
- [x] Deterministic fallback keeps the endpoint from `500`-ing on LLM failure.
- [x] OpenAPI docs expose the endpoint.
- [x] Ruff (backend) and ESLint (frontend) clean.
- [ ] Unit + integration tests written and passing. _(gap — tracked)_
- [ ] Retry-vs-`503` decision for transient LLM failure resolved. _(open)_
