# Phase 5 - Cohort Match Run & Export - Implementation Plan

## 1. Database Schema & Cache Persistence

- **Module**: `backend/app/features/matching/models.py`
- **Details**:
  - Defines the `batch_pair_scores` cache table.
  - Fields include `candidate_id`, `project_id`, `preliminary_score`, and individual sub-score floats.

## 2. Matrix Scoring & Cache Service

- **Module**: `backend/app/features/matching/service.py`
- **Details**:
  - `compute_batch_scores` retrieves all candidates and eligible projects in the batch.
  - If cached records exist for this batch, they are loaded immediately.
  - If `force=True` or the cache is missing, old rows are deleted and the matching engine recomputes Stage-1 preliminary scores for all candidate-project pairs, bulk-inserting them into `batch_pair_scores`.

## 3. Frontend Operator Dashboard

- **Module**: `frontend/src/components/dashboard/BatchScoreMatrix.tsx` and `App.tsx`
- **Details**:
  - `BatchScoreMatrix.tsx` handles matrix queries and updates.
  - Renders a Student Tile Grid displaying:
    - Composite scores with colored progress bars (e.g. Green for strong, Amber for moderate, Red for weak).
    - Grid columns showing the 4 sub-scores (Embed, Prereq, Resume, Pref) side-by-side.
  - Implements client-side sorting: Best Match, Average Score, and A-Z.
