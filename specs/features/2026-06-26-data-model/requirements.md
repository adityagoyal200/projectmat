# Phase 1 Data Model - Requirements

## Scope

Create the normalized relational schema required for import batches, canonical records, match runs, match results, and auditability.

## Deliverables

- Tables: `import_batches`, `import_files`, `import_validation_issues`, `candidates`, `candidate_contacts`, `candidate_documents`, `candidate_skills`, `candidate_embeddings`, `mentors`, `mentor_contacts`, `projects`, `project_prerequisites`, `project_preferences`, `project_embeddings`, `match_runs`, `match_results`, `match_result_explanations`, Shared `skills`, `technologies`, `tags`, and `audit_logs`.

## Context & Decisions

- Use SQLAlchemy 2.0 Async + Alembic.
- Strict normalization for all entities. No JSON columns for core business data; only for audit snapshots or unstructured metadata.
- PostgreSQL 15+ with pgvector for embeddings.
