# Phase 5 - Cohort Match Run & Export - Requirements

## Status

`[x] Done`

## Author

Antigravity

## Date

2026-06-29

## Related Phase

Phase 5 - Cohort Match Run & Export

## 1. Problem Statement

Evaluating candidate-project pairs one-by-one is tedious. Program operators need a comprehensive, cohort-wide view (matrix) of scores for all candidates and projects in an import batch. To make this review responsive, the system must cache deterministic calculations in the database to avoid repeating expensive embeddings or parser checks. Additionally, operators need an interactive user interface to sort, filter, and inspect these scores.

## 2. Proposed Solution

1. **Deterministic Database Caching**: Implement `batch_pair_scores` table to persist Stage-1 preliminary scores for every candidate-project pair in a batch.
2. **Matrix Endpoint**: Expose `GET /api/matching/batch-scores/{batch_id}` to retrieve scores, with a `force` query parameter to clear the cache and recompute from scratch.
3. **Interactive Admin UI**: Integrate React frontend components (`BatchScoreMatrix.tsx`) showing a student tile grid, color-coded composite scores, sub-score visualizations, and sorting filters.

## 3. User Stories

- As an **Operator**, I want to **view a matrix of candidate-project scores for an entire import batch**, so that **I can review the program allocation strategy at a glance**.
- As an **Operator**, I want the **matrix scores to load quickly**, so that **I do not experience latency from repeated AI scoring**.
- As an **Operator**, I want to **sort candidate cards by score strengths**, so that **I can isolate weak matches requiring intervention**.

## 4. Input and Output Contracts

### Inputs

- Import batch ID.
- Recalculation bypass flag (`force`).

### Outputs

- Complete list of pair scores with sub-score components, cached and ready to render.

## 5. Scope

### In Scope

- Database schema changes supporting pair score caching.
- Synchronous matrix calculations and database persistence.
- React components displaying visual grids, color-coded score indicators (strong, moderate, weak), and sorting options (best match, average, alphabetical).

### Out of Scope

- Automated matching optimization models (deferred).
- Multi-operator collaborative workspace notes (deferred).

## 6. API Design

| Method | Path                                    | Description                                           | Roles      |
| ------ | --------------------------------------- | ----------------------------------------------------- | ---------- |
| `GET`  | `/api/matching/batch-scores/{batch_id}` | Return cached deterministic scores for student-pairs. | `operator` |

## 7. Definition of Done

- [x] Matrix scores are computed, persisted, and cached in PostgreSQL.
- [x] Database cache is cleared and re-initialized when `force=true` is requested.
- [x] The React Student Tile Grid renders composite and sub-scores.
- [x] Sorting and visual color-coding are implemented on the frontend.
