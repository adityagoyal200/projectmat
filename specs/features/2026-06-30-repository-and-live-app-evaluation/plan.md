# Phase 6 - GitHub Repository & Live App Evaluation - Implementation Plan

## 1. Domain Clients & Data Gathering

1. **GitHub Client**: Create `github_client.py` for fetching user profile details, public repository lists, push activity, and search parameters for public PRs. Add authentication header support via `settings.GITHUB_TOKEN`.
2. **LeetCode Client**: Create `leetcode_client.py` utilizing the LeetCode GraphQL endpoint to query total problems solved, difficulty distributions (easy, medium, hard), and contest attendance metrics.
3. **Codeforces Client**: Create `codeforces_client.py` to retrieve rating achievements and max ranks using the Codeforces public REST API.
4. **Google Scholar Client**: Create `scholar_client.py` with HTML regex parsers to scrape citations, publications counts, and h-indexes.

## 2. Database & Schema Configuration

1. **Candidate Table Updates**: Append fields to `candidates` table to store extracted usernames (GitHub, LeetCode, Codeforces, Kaggle, Scholar), cached metrics JSON blobs, achievements JSON, repository URL lists, and live app link lists.
2. **Repository Evaluations Table**: Add table `repository_evaluations` linked to candidates via cascade delete relationships to store code analysis metrics, findings, execution logs, and AI evaluation summaries.
3. **Live App Evaluations Table**: Add table `live_app_evaluations` linked to candidates to persist response times, console error counts, agent interaction trace logs, and screenshots.
4. **Alembic Migration**: Auto-generate schema migration and execute async DB upgrades.

## 3. Static Repository Scanner

1. **File Traverser**: Implement directory traversers skipping environment or build directories (`.git`, `node_modules`, `.venv`).
2. **Secrets Scanner**: Add regex indicators matching RSA private keys and api/secret/token strings.
3. **Test Detector**: Detect `package.json` scripts or pytest modules to construct automated commands.
4. **Sandboxed Command Execution**: Use subprocess forks to run detected test commands with timeouts, capturing outputs in `execution_log`.
5. **AI Logic Reviewer**: If LLM is active, extract the top 3 code files and send them to the centralized generation provider to return logical cleanliness scores.

## 4. Live App Browser Crawler

1. **Wakeup & Navigations**: Initialize Playwright headless chromium sessions with cold-start wakeup tolerance (45s) and navigation retries.
2. **Tab Hydration Check**: Query for common tab links ("dashboard", "details") and simulate clicks.
3. **Trace Logger**: Log reasoning, actions, and observations into an `agent_trace` list.
4. **Visual Verification**: Take high-res screenshots and save them locally under `screenshots/`.

## 5. API Endpoints

1. Implement FastAPIs under `router.py` to read/refresh evaluations:
   - `GET /api/evaluations/candidates/{candidate_id}`
   - `POST /api/evaluations/candidates/{candidate_id}/refresh`
   - `POST /api/evaluations/candidates/{candidate_id}/repositories`
   - `POST /api/evaluations/candidates/{candidate_id}/live-apps`
   - `POST /api/evaluations/batches/{batch_id}/refresh`

## 6. Scoring Pipeline Integration

1. Update `scoring.py` to compile `compute_developer_profile_score` by calculating:
   - GitHub stars, followers, and public PR counts.
   - Codeforces ratings and LeetCode problem difficulty indexes.
   - Scholar citations and publication records.
2. Update weights to assign 30% for GitHub/Repository, 5% for Coding Profiles, and 5% for Achievements/Scholar scores (retuned from an earlier 20%/10% draft; embedding 15%, prerequisite 20%, resume experience 20%, LLM fit 5% — scoring v3.1.0 in `backend/app/config.py`).
3. Cache these deterministic evaluations in `batch_pair_scores` matrix tables.
