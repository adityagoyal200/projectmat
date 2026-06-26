# Phase 1 Data Model - Plan

1. **Task 1: Setup migrations**

   - Initialize Alembic environment if not present.
   - Configure async SQLAlchemy connection in Alembic.

2. **Task 2: Import tables**

   - Create models for `import_batches`.
   - Create models for `import_files`.
   - Create models for `import_validation_issues`.

3. **Task 3: Candidate & Mentor tables**

   - Create models for `candidates`, `candidate_contacts`, `candidate_documents`, `candidate_skills`, `candidate_embeddings`.
   - Create models for `mentors`, `mentor_contacts`.
   - Create shared models for `skills`, `technologies`, `tags`.

4. **Task 4: Project & Match tables**

   - Create models for `projects`, `project_prerequisites`, `project_preferences`, `project_embeddings`.
   - Create models for `match_runs`, `match_results`, `match_result_explanations`.
   - Create models for `audit_logs`.

5. **Task 5: Unit testing**
   - Write unit tests validating model relationships and constraints.
   - Test Alembic migration apply and rollback.
