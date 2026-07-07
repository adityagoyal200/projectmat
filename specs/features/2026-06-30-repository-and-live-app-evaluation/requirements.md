# Phase 6 - GitHub Repository & Live App Evaluation - Requirements

## Status

`[x] Done`

## Author

Antigravity

## Date

2026-06-30

## Related Phase

Phase 6 - GitHub Repository & Live App Evaluation

---

## 1. Problem Statement

To transition beyond superficial resume scanning, program operators need to evaluate candidates based on their actual code artifacts (GitHub repositories), competitive coding rankings (LeetCode, Codeforces, Kaggle), academic publications (Google Scholar), and live application performance.

This requires:

1. Extracting developer profiles and project URLs from resumes.
2. Interrogating public developer profile metrics (repos, stars, contest stats, publications).
3. Analyzing repository structures statically for code hygiene, tests, and security.
4. Performing live application validation via browser crawls (checking for status, errors, latency, loading states).
5. Integrating these multi-dimensional scores into the final matching matrix.

---

## 2. Proposed Solution

Build a modular evaluations engine (`features/evaluations/`) that runs both static inspection and automated crawls, persists evaluations in dedicated database tables, and calculates a multi-dimensional developer score which feeds directly into the hybrid matching engine.

The architecture uses:

- **Profile Clients**: Low-overhead HTTP scanners for GitHub (REST API), LeetCode (GraphQL), Codeforces (REST API), and Google Scholar (HTML parsing).
- **Repository Evaluator**: An inspector for local/cloned checkouts that scans file structures, detects secrets, checks dependency manifests, discovers test suites, and runs tests inside a sandbox environment (opt-in).
- **Live App Evaluator**: A Playwright browser agent that wake-ups, interacts with, screenshots, and logs browser errors/console issues for live application URLs.
- **Service & Routers**: APIs under `/api/evaluations/` for candidate-level and batch-level refresh/query.

---

## 3. Data Model Changes

Adds two new tables to record evaluations over time:

### `repository_evaluations`

| Column               | Type         | Description                                                     |
| -------------------- | ------------ | --------------------------------------------------------------- |
| `id`                 | Integer (PK) | Auto-incrementing identifier.                                   |
| `candidate_id`       | Integer (FK) | References the canonical candidate.                             |
| `repository_url`     | String(1024) | The Git repository url.                                         |
| `repository_name`    | String(255)  | Parsed repo name.                                               |
| `source`             | String(50)   | Source of extraction (e.g., `resume`).                          |
| `status`             | String(50)   | Status (`completed`, `failed`, `completed_with_errors`).        |
| `score`              | Float        | Aggregated deterministic score (0.0-1.0).                       |
| `metrics`            | JSONB        | File counts, languages, README present, etc.                    |
| `findings`           | JSONB        | Structured warning/error issues (secrets, missing tests, etc.). |
| `execution_log`      | Text         | Output logs from running test commands.                         |
| `github_logic_score` | Float        | AI Code Review score (0.0-1.0).                                 |
| `ai_justification`   | Text         | AI justification/notes.                                         |
| `evaluated_at`       | DateTime     | Evaluated timestamp.                                            |

### `live_app_evaluations`

| Column            | Type         | Description                                                                  |
| ----------------- | ------------ | ---------------------------------------------------------------------------- |
| `id`              | Integer (PK) | Auto-incrementing identifier.                                                |
| `candidate_id`    | Integer (FK) | References the canonical candidate.                                          |
| `url`             | String(1024) | Live application link.                                                       |
| `source`          | String(50)   | Source of extraction (e.g., `resume`).                                       |
| `status`          | String(50)   | Status (`completed`, `completed_with_errors`, `unreachable`, `invalid_url`). |
| `score`           | Float        | Aggregated rubric score (0.0-1.0).                                           |
| `http_status`     | Integer      | HTTP status code returned.                                                   |
| `latency_ms`      | Integer      | Page load response latency in ms.                                            |
| `metrics`         | JSONB        | Page title, console errors, screenshot status, etc.                          |
| `findings`        | JSONB        | Structured page warnings/errors.                                             |
| `agent_trace`     | JSONB        | Step-by-step browser interactions (Reason -> Act -> Observe).                |
| `screenshot_path` | String(1024) | Path to page screenshot.                                                     |
| `evaluated_at`    | DateTime     | Evaluated timestamp.                                                         |

---

## 4. Input and Output Contracts

### Inputs

- **Candidate Profiles**: Parsed GitHub, LeetCode, Codeforces, Kaggle handles, and Scholar IDs.
- **Repository URLs**: Git URLs extracted from candidate resumes.
- **Live URLs**: Live application links extracted from candidate resumes.

### Outputs

- **Candidate Summary**: JSON response detailing developer handles, metrics, repository scans, and live app traces.
- **Score Matrix**: Persisted sub-scores feeding into the `final_score` composite score.

---

## 5. Scope

### In Scope

- Automatic parsing of developer profile links from resumes.
- Rate-limit friendly scraping clients for public developer websites.
- Local repository folder analysis (structural composition, secret warnings, README/License/Dependency checks).
- Explicit, opt-in remote Git cloning and sandboxed local test execution.
- Autonomous Playwright browser evaluation with console error observation, navigation wakeups, and screenshot capture.
- Incorporation of Phase 6 scores into matching matrix.

### Out of Scope

- Dynamic test code generation (restricted to execution of already present test suites).
- Student/Mentor auth wrappers (deferred).

---

## 6. Scoring Weights (SCORING_VERSION: 3.1.0)

> Source of truth: `backend/app/config.py`. Weights were retuned from the initial
> v3.0.0 draft (which used Coding 20% / Resume 10% / Embedding 10% / Achievements 10%
> / Prereq 15%) after GitHub/repository quality proved the stronger deterministic
> signal. Current v3.1.0 weights below sum to 100%.

| Score Component           | Weight | Source                        | Description                                                                                                                                       |
| ------------------------- | ------ | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **GitHub Score**          | 30%    | `github_metrics` & Repo scans | Bounded counts for stars, followers, public PRs, OS contributions, repo count, static repo evaluation quality, and repository logic review.       |
| **Prerequisite Overlap**  | 20%    | Resume parsing vs Project     | Tiered overlap (Exact/Alias = 1.0, Adjacent/Family = 0.5, Gaps = 0.0).                                                                            |
| **Resume Experience**     | 20%    | Resume vs Project abstract    | Depth of work, domain keywords, and project occurrences.                                                                                          |
| **Embedding Similarity**  | 15%    | pgvector                      | Cosine distance similarity.                                                                                                                       |
| **Coding Profiles Score** | 5%     | LeetCode & Codeforces         | Calculated from LeetCode solved problems (weighted by difficulty: Easy=1, Medium=2, Hard=3), contest count, Codeforces rating, and Kaggle medals. |
| **Achievements Score**    | 5%     | Resume achievements & Scholar | Citations, publications, h-index, and resume awards/ICPC heuristics.                                                                              |
| **LLM Fit Score**         | 5%     | LLM review                    | Small qualitative fit score (0.0-1.0).                                                                                                            |

---

## 7. API Design

| Method | Path                                                      | Description                                              | Roles      |
| ------ | --------------------------------------------------------- | -------------------------------------------------------- | ---------- |
| `GET`  | `/api/evaluations/candidates/{candidate_id}`              | Fetch summary of candidate profiles and evaluations.     | `operator` |
| `POST` | `/api/evaluations/candidates/{candidate_id}/refresh`      | Trigger refresh of profile metrics and evaluation URLs.  | `operator` |
| `POST` | `/api/evaluations/candidates/{candidate_id}/repositories` | Manually run static and execution tests for a Git repo.  | `operator` |
| `POST` | `/api/evaluations/candidates/{candidate_id}/live-apps`    | Manually run a Playwright browser crawl for a live URL.  | `operator` |
| `POST` | `/api/evaluations/batches/{batch_id}/refresh`             | Refresh evaluations for an entire workbook import batch. | `operator` |
