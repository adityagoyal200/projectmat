# ProjectMatchAI - Development Process, Prompts, and Tools

> Reference document — summarizes how this project is actually built: the spec-driven process, the Claude Code skills/prompts that drive it, and the tools used for implementation and verification. Written from the current state of `specs/`, `README.md`, and recent working sessions.

---

## 1. Governing documents ("constitution")

Every phase and feature is required to respect four standing documents before any code is written:

| Document                 | Purpose                                                                                                              |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| `specs/00-principles.md` | Engineering constraints (YAGNI, KISS, backend-boundary-first, feature-first, etc.). Principles win over convenience. |
| `specs/mission.md`       | What the product is and who it's for (operators, mentors, students, future integrations).                            |
| `specs/tech-stack.md`    | Approved architecture style, repo layout, and technology choices. No new dependencies without approval.              |
| `specs/roadmap.md`       | Phase-by-phase plan (MVP phases 0-5, Post-MVP tiers A/B/C) with status per phase.                                    |

Architecture decisions with real trade-offs additionally require an **ADR** under `specs/adrs/` (see `ADR-0001-standalone-bulk-intake-matching-mvp.md`) before production code.

---

## 2. Feature spec lifecycle

Each feature lives in a dated directory: `specs/features/YYYY-MM-DD-<feature-name>/`, containing three files, all copied from `specs/templates/`:

1. **`requirements.md`** (from `feature-template.md`) — problem statement, user stories, input/output contracts, in/out of scope, solution options + trade-offs, API design, data model changes, service design, AI/generation components, frontend components, validation plan, definition of done, open questions.
2. **`plan.md`** — numbered, independently-implementable task groups (e.g. Data → Components → Page & Route → Navigation → Tests).
3. **`validation.md`** (from `validation-template.md`) — automated checks (tests/typecheck commands + specific assertions), manual walkthrough steps, tone check for user-facing copy, and a definition-of-done checklist.

API contracts that need full endpoint detail get a matching file under `specs/apis/` (from `api-template.md`), e.g. `specs/apis/bulk-intake-and-matching-api.md`.

Feature directories created so far:

- `2026-06-26-data-model`
- `2026-06-26-bulk-workbook-import`
- `2026-06-26-bulk-intake-and-matching`
- `2026-06-27-in-memory-ingest-and-profile-normalization`
- `2026-06-28-symmetrical-matching-and-recommendation-apis`
- `2026-06-29-cohort-match-run-and-export`
- `2026-06-30-repository-and-live-app-evaluation`
- `2026-07-03-candidate-project-fit-report`

---

## 3. Claude Code skills used as "prompts" for the process

These are invoked as slash commands / triggers inside Claude Code and encode the repeatable parts of the workflow:

| Skill             | Trigger                                                 | What it does                                                                                                                                                                                                                                                                                                                                 |
| ----------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `feature-spec`    | `/feature-spec`, "start the next feature", "next phase" | Reads `specs/roadmap.md` for the next incomplete phase, creates a branch (`phase-N-<name>`), interviews the user with 3 fixed questions (Scope / Decisions / Context) via `AskUserQuestion` **before writing any files**, reads `mission.md` + `tech-stack.md`, then writes the dated `requirements.md` / `plan.md` / `validation.md` triad. |
| `changelog`       | `/changelog`, "update the changelog"                    | Runs `specs/skills/changelog/scripts/changelog.py` from the project root; builds or appends to root `CHANGELOG.md` grouped by `## YYYY-MM-DD` headings, one bullet per commit subject, idempotent re-runs.                                                                                                                                   |
| `code-review`     | `/code-review [low\|medium\|high\|xhigh\|max\|ultra]`   | Reviews the current diff for correctness bugs + reuse/simplification/efficiency issues at the requested effort level; `ultra` runs a multi-agent cloud review. Supports `--comment` (inline PR comments) and `--fix` (apply findings).                                                                                                       |
| `security-review` | "security review"                                       | Runs a security review of pending changes on the current branch (OWASP-style).                                                                                                                                                                                                                                                               |
| `simplify`        | —                                                       | Reviews changed code for reuse/simplification/efficiency and applies fixes directly (quality only, not bug-hunting).                                                                                                                                                                                                                         |
| `verify`          | —                                                       | Exercises the actual affected flow end-to-end (not just tests/typecheck) before a nontrivial change is considered done.                                                                                                                                                                                                                      |
| `run`             | —                                                       | Finds or falls back to a pattern for actually launching the app (CLI/server/TUI/Electron/browser/library) and driving one representative interaction to a screenshot/output, proving it works rather than just compiles.                                                                                                                     |

---

## 4. Definition-of-done checklist (applies to every feature)

From the feature template, repeated per feature's `validation.md`:

- [ ] Architecture approved (ADR if needed)
- [ ] Endpoints return correct status codes/schemas
- [ ] Service methods have unit tests; endpoints have integration tests
- [ ] AI fallback behavior tested where relevant
- [ ] Alembic migration applies and rolls back cleanly where relevant
- [ ] FastAPI OpenAPI docs verified
- [ ] README / `.env.example` updated if setup changed
- [ ] Ruff (backend) and ESLint (frontend) pass with zero warnings
- [ ] No `any` types in new TypeScript
- [ ] No raw SQL in service/router layers
- [ ] No direct LLM calls outside `ai/generation/`

---

## 5. Toolchain

**Backend** (`backend/`)

- FastAPI + SQLAlchemy + Alembic, Python 3.11+
- `pytest` — unit + integration tests (`backend/tests/unit`, `backend/tests/integration`)
- `ruff check .` — lint/format gate
- PostgreSQL via `docker compose up -d`

**Frontend** (`frontend/`)

- Vite + React + TypeScript, Tailwind
- `npm run lint` (ESLint), `npm run build` (`tsc && vite build`), `npm run test` (Vitest)
- `npx tsc --noEmit` for a fast standalone typecheck

**Document generation**

- PyMuPDF (`fitz`) Story engine — server-side HTML→PDF rendering for the candidate–project fit report (`app/features/matching/report.py`). Reuses the library already bundled for in-memory resume parsing, so no new dependency was added. Rendering runs off the event-loop thread via `asyncio.to_thread`.

**Verification / UI proof**

- Playwright (`npx playwright install chromium`, driven via a throwaway `.cjs` script) or the `chromium-cli` REPL where available — used to actually load the dev server, hover/click elements, and screenshot the result rather than relying on typecheck alone.
- Temporary harness components (e.g. mounting a single component with mock data through a scratch `main.tsx` swap) when exercising a component in isolation is faster than standing up the full backend + imported dataset; always reverted after the check.

**Version control / review**

- Git, with commit messages authored from the actual diff + `git log` style, never `--amend` on published work, never destructive resets without explicit confirmation.
- `gh` CLI for PRs when requested.

---

## 6. Example: applying the process to a bug fix (tooltip clipping, 2026-07-02)

Not every change is a full roadmap phase — small bug fixes still follow the "understand → fix → prove it works" shape without spinning up a full feature-spec directory:

1. **Diagnose** — read the three components involved (`ScoreCalculation.tsx`, `ScoreBar.tsx`, `RecommendationCard.tsx`) and traced the bug to absolutely-positioned tooltip `<div>`s nested inside ancestors with `overflow-hidden` / `overflow-x-auto`, which clipped the popover text.
2. **Fix** — built one reusable `frontend/src/components/ui/Tooltip.tsx` that portals its panel to `document.body` and self-positions via `getBoundingClientRect` (flips above the trigger and clamps horizontally when near a viewport edge), then swapped all four ad-hoc tooltip instances over to it.
3. **Static checks** — `npx tsc --noEmit` and `npx eslint <changed files>` clean.
4. **Runtime proof** (`run`/`verify` pattern) — spun up the Vite dev server against a temporary mock-data harness placed far down a long scrollable page, drove it with a throwaway Playwright script (`chromium.launch()` → `hover()` → `screenshot()` → `console --errors` check), confirmed both tooltips rendered fully and unclipped, then deleted all scratch scripts/screenshots and reverted `main.tsx` to its original state.

This mirrors the same discipline the feature-spec process encodes — verify behavior, not just types — just scoped down for a change too small to need its own `requirements.md`/`plan.md`/`validation.md` triad.

---

## 7. Example: verifying a feature end-to-end (fit-report generation, 2026-07-07)

Generating a real fit-report PDF followed the same "run it, observe it, don't trust the happy path" shape:

1. **Orient** — read `report.py`, the `MatchService.build_match_report` path, and the `GET /api/matching/report` route to confirm what the endpoint needs (a candidate + project in the DB and a configured LLM).
2. **Check the running state** — confirmed Postgres (Docker) and the backend on `:8000` were already up, the OpenAPI served `200`, and the DB held real candidates/projects.
3. **Pick a meaningful pair** — called `GET /api/matching/student-recommendations/{reg}` to rank a student's projects and chose their top _real_ (non-dummy) match rather than an arbitrary pair.
4. **Generate + inspect** — hit the report endpoint, then extracted the PDF text with PyMuPDF and asserted every section was present.
5. **Catch the silent failure** — the first run fell back to the empty deterministic skeleton ("Automated analysis was unavailable"). Reproduced the LLM analysis call in isolation, confirmed it succeeded, and diagnosed a transient rate-limit/timeout (the report path fires several LLM calls right after a 12-call recommendations run). Re-ran → full 3-page report. Logged the "no retry on the analysis call" gap into the feature's `requirements.md` Open Questions.

The lesson reinforced by this session: a `200` is not proof of a good report — the deliverable has to be opened and read, because the fallback path returns success with empty content.

---

## 8. Prompts used to drive development (quick index)

The "prompts" in this project are the skills in §3 plus the fixed interview the `feature-spec` skill asks before writing any files (Scope / Decisions / Context via `AskUserQuestion`). The LLM _product_ prompts — distinct from the development prompts — live in code and are the source of truth:

| Product prompt                                  | Location                                            | Purpose                                                                                                                                                           |
| ----------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Symmetrical match evaluation (student / mentor) | `matching/match_explanation.py::_build_eval_prompt` | Structured JSON scores + qualitative paragraphs, grounded in resume + developer-profile signals.                                                                  |
| Readiness / improvement analysis                | `matching/report.py::generate_improvement_analysis` | Structured JSON (fit summary, assessment, strengths, gaps, plan, roadmap, resources, approach, risks) for the PDF report, with a deterministic-skeleton fallback. |
| LLM provider preview                            | `matching/router.py::/llm-preview`                  | Ad-hoc prompt to sanity-check the configured provider before enabling matching.                                                                                   |

All product LLM calls route through `matching/llm_client.generate_chat_completion` (the single generation boundary); there are no ad-hoc provider calls in routers/services.
