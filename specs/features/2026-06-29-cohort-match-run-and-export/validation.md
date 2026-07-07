# Phase 5 - Cohort Match Run & Export - Validation Plan

## 1. Acceptance Criteria

- **AC-1**: Preliminary pair scores are persisted to the database.
- **AC-2**: Recompute matrix triggers cleanly with `force=true`.
- **AC-3**: The React UI updates when a different batch is selected.
- **AC-4**: Sorting matches candidates with highest score first.

## 2. Automated Verification

- Run API checks ensuring the matrix data complies with schemas:
  - `GET /api/matching/batch-scores/{batch_id}` returns a JSON list of matches containing expected properties (`candidate_id`, `project_id`, sub-scores, etc.).

## 3. Manual UI Verification

- Select an import batch in the operator dashboard and confirm:
  - Loading animation triggers and resolves.
  - Candidate tiles render colored progress bars representing composite scores.
  - Sub-scores are displayed clearly.
  - Clicking sorting buttons updates card rankings.

## 4. Definition of Done

- [x] Matrix API integration tests pass.
- [x] UI component compilation builds cleanly.
- [x] Code formatting checks succeed.
