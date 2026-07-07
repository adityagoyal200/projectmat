# Phase 4 - Symmetrical Matching & Recommendation APIs - Validation Plan

## 1. Acceptance Criteria

- **AC-1**: Standard student profiles and projects are mapped to pgvector collections.
- **AC-2**: Recommendations endpoints list matching candidate/project pairs sorted by descending score.
- **AC-3**: Recommendations are returned synchronously for on-the-fly resume PDF uploads.
- **AC-4**: Explainable justifications are displayed or default to backup text when LLM configurations fail.

## 2. Unit Tests

- `test_scoring`: Validates the formulas for prerequisite overlap, resume experience, and composite final score.
- `test_match_explanation`: Ensures the explanation system compiles valid responses and fallbacks.
- `test_skill_aliases`: Verifies matching across spelling aliases and related skill families.

## 3. Integration Tests

- `test_matching_api`: Executes client uploads and queries requests against standard recommendation endpoints, verifying response structures.

## 4. Edge Cases

- Ambiguous preferences: Preferences linking to missing rows or invalid candidate details default gracefully.
- LLM Timeouts: LLM service failure times out cleanly after a threshold and returns deterministic fallbacks.
- Empty profiles: Candidates with missing skill structures receive default low scores instead of causing runtime exceptions.

## 5. Definition of Done

- [x] Symmetrical routing unit tests pass.
- [x] Embeddings are mapped and tested via test databases.
- [x] Type validations check out clean.
