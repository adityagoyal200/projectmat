# Phase 6 - GitHub Repository & Live App Evaluation - Validation Plan

## 1. Acceptance Criteria

- **AC-1**: Profile URLs (GitHub, LeetCode, Codeforces, Kaggle, Scholar) are successfully extracted from candidate resumes.
- **AC-2**: Public developer metrics are scraped accurately and stored without API blockages or runtime crashes.
- **AC-3**: Static repository scans analyze files, flag secret tokens, identify READMEs/licenses/manifests, and execute automated test suites (with explicit opt-in).
- **AC-4**: Playwright browser crawls capture HTTP status code, latency, console log exceptions, page titles, and high-quality verification screenshots.
- **AC-5**: Final recommendation composites reflect correct weights for GitHub (30%), coding profile (20%), and achievements (10%).

## 2. Unit Tests

- `test_github_client_user_metrics`: Verify GitHub client processes mock payload.
- `test_leetcode_graphql_parse`: Check GraphQL queries handle correct stats format.
- `test_codeforces_profile_rating`: Check Codeforces client fetches rating and handle details.
- `test_scholar_citations_regex`: Validate citation and publication parsing from mock Scholar HTML page.
- `test_scan_secrets_regex`: Confirm secret detector flags committed keys and API tokens.
- `test_run_tests_subprocess`: Ensure sandbox test execution manages process forks and timeout limits.
- `test_compute_developer_profile_score`: Validate profile rubric score outputs correct floats.

## 3. Integration Tests

- `test_get_candidate_evaluations_endpoint`: Querying `/api/evaluations/candidates/{id}` returns candidate summary.
- `test_refresh_candidate_evaluations`: Executing refresh updates metrics and evaluation database caches.
- `test_evaluate_repository_api`: POST on `/api/evaluations/candidates/{id}/repositories` runs repo scanning.
- `test_evaluate_live_app_api`: POST on `/api/evaluations/candidates/{id}/live-apps` runs Playwright crawl.

## 4. Edge Cases

- **Rate Limits**: Scraping clients fail gracefully (returning structured error metrics) when APIs rate limit them.
- **Cold Starts**: Render/Streamlit services wake up successfully within the extended 45-second Playwright timeout.
- **Invalid URLs**: Broken links generate warning status flags instead of crashing the batch process.
- **Huge Repositories**: Scanners ignore file objects larger than 256KB to avoid memory bloat.

## 5. Definition of Done

- [ ] All client unit tests are written and passing.
- [ ] Router integration tests succeed on test DB.
- [ ] No regression in core matching pipeline scores.
- [ ] Type validation checks pass.
- [ ] Ruff formatting check returns clean.
