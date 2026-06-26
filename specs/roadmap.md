# ProjectMatchAI - Implementation Roadmap

> Constitution Document - Version 4.0 - June 2026
> This roadmap reflects the revised product scope: ProjectMatchAI is a standalone upload-and-review app for bulk intake and AI matching, with a backend boundary that can support future integration.

---

## Guiding Principles

- The MVP validates upload, import, matching, explanation, and result review.
- Every phase produces a reviewable artifact.
- Every feature starts with a spec under `specs/features/`.
- Architecture decisions with meaningful trade-offs require ADRs under `specs/adrs/`.
- Tests are part of every phase's Definition of Done.
- No task queue, dedicated vector database, full auth portal, chat, or notifications until the roadmap requires them.

---

## Tier Overview

```text
MVP (Phases 0-10)
  Proves: messy candidate/project data can be imported, normalized, matched, explained, and exported.

Post-MVP A - Operator UX and Deployment Readiness
  Adds: complete review UI, operator auth, deployment hardening, and optional external API contracts.

Post-MVP B - Quality and Feedback
  Adds: reviewer feedback loops, AI evaluation, scoring iteration, and outcome analytics.

Post-MVP C - Portal and Integration Features
  Adds: student/mentor dashboards, roadmaps, chat, notifications, and admin features only if needed.
```

---

## Phase Summary

| Phase    | Name                              | Status      |
| -------- | --------------------------------- | ----------- |
| Phase 0  | Project Setup                     | Completed   |
| Phase 1  | Data Model                        | Not Started |
| Phase 2  | Bulk Workbook Import              | Not Started |
| Phase 3  | Resume File Intake                | Not Started |
| Phase 4  | Candidate Profile Normalization   | Not Started |
| Phase 5  | Mentor and Project Normalization  | Not Started |
| Phase 6  | Embedding Service                 | Not Started |
| Phase 7  | Match Run Orchestration           | Not Started |
| Phase 8  | Reranking and Hybrid Scoring      | Not Started |
| Phase 9  | Match Explanations                | Not Started |
| Phase 10 | Result Export and Review Contract | Not Started |

| Post-MVP | Name                               | Status      |
| -------- | ---------------------------------- | ----------- |
| A1       | Complete Operator Review UI        | Not Started |
| A2       | Operator Auth and Access Hardening | Not Started |
| A3       | External Integration API           | Deferred    |
| B1       | Reviewer Feedback Capture          | Not Started |
| B2       | AI Evaluation Framework            | Not Started |
| B3       | Scoring Calibration                | Not Started |
| C1       | Student Experience                 | Deferred    |
| C2       | Mentor Experience                  | Deferred    |
| C3       | Notifications and Chat             | Deferred    |
| C4       | Admin Panel                        | Deferred    |
| C5       | Production Deployment Hardening    | Not Started |

---

# MVP - Phases 0-10

## MVP Goal

A program operator can provide:

- A workbook with student/candidate rows.
- Optional resume files or resume file references.
- A workbook with mentors and projects.

ProjectMatchAI can then:

- Validate the imported data.
- Normalize candidates, mentors, projects, skills, and prerequisites.
- Run an explicit match job.
- Produce ranked candidates per project.
- Provide score breakdowns and grounded explanations.
- Export or return results for human review.

---

## Phase 0 - Project Setup

### Goal

Establish a runnable monorepo foundation.

### Status

Completed.

### Notes

The existing setup remains valid, but subsequent phases are re-scoped around subsystem ingestion and matching rather than standalone auth/dashboard development.

---

## Phase 1 - Data Model

### Goal

Create the normalized relational schema required for import batches, canonical records, match runs, match results, and auditability.

### Deliverables

- `import_batches`
- `import_files`
- `import_validation_issues`
- `candidates`
- `candidate_contacts`
- `candidate_documents`
- `candidate_skills`
- `candidate_embeddings`
- `mentors`
- `mentor_contacts`
- `projects`
- `project_prerequisites`
- `project_preferences`
- `project_embeddings`
- `match_runs`
- `match_results`
- `match_result_explanations`
- Shared `skills`, `technologies`, `tags`, and `audit_logs`

### Definition of Done

- Alembic migration applies and rolls back cleanly.
- Foreign keys and uniqueness constraints prevent duplicate canonical records within an import batch.
- Source row snapshots are stored only as audit metadata, not primary business data.
- Unit tests validate model relationships where useful.

### Dependencies

- Phase 0

---

## Phase 2 - Bulk Workbook Import

### Goal

Import workbook data into typed staging records with explicit validation issues.

### Supported MVP Workbook Sheets

Based on the provided reference workbook:

| Sheet               | Purpose                                  | Key Columns                                                                                                                                                                                              |
| ------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Students Info`     | Candidate identity and resume references | `Name`, `Registration Number`, `Email`, `Phone`, `File`                                                                                                                                                  |
| `Mentors info`      | Mentor identity and contact data         | `Mentors`, `email id`                                                                                                                                                                                    |
| `Mentors-projects`  | Mentor project data and selections       | `Mentors`, `Short profile of the mentor`, `Project Title`, `Project Abstract`, `Pre-requisites`, `Student's Preference - 1`, `Student's Preference - 2`, `Student's Preference - 3`, `Selected students` |
| `Probable projects` | Optional project ideas                   | `Project Idea`, `Author`, `Topic`                                                                                                                                                                        |

### Deliverables

- Workbook parser isolated under `features/imports/`.
- Header alias map for expected sheet and column names.
- Import batch creation endpoint.
- Row-level validation issue records.
- Source sheet and row number retained for every staged record.

### Definition of Done

- Valid workbook produces an `import_batch` and staged rows.
- Missing required sheets or columns produce structured validation issues.
- Duplicate registration numbers, invalid emails, missing project titles, missing mentor names, and unknown resume references are reported.
- Parser unit tests cover representative messy rows from the reference workbook.

### Dependencies

- Phase 1

---

## Phase 3 - Resume File Intake

### Goal

Link candidate records to resume files uploaded with an import batch.

### Deliverables

- Resume file registration endpoint.
- Candidate-to-document linking by file name, registration number, or explicit mapping.
- File type and size validation.
- Document parse status tracking.

### Definition of Done

- Candidate rows with `File` values can be linked to stored resume files.
- Missing resume files produce warnings, not hard import failure.
- Invalid files are rejected with clear errors.
- Integration tests cover file registration and candidate linking.

### Dependencies

- Phase 2

---

## Phase 4 - Candidate Profile Normalization

### Goal

Create canonical candidate profiles from imported spreadsheet fields plus optional resume parsing.

### Deliverables

- Digital PDF parsing through PyMuPDF.
- OCR fallback through PaddleOCR when needed.
- Structured parsed profile schema.
- Skill and technology normalization into canonical registries.
- Candidate profile confidence and source provenance.

### Definition of Done

- Candidate records exist even when resumes are missing.
- Resume-derived skills are stored as normalized candidate skills with source metadata.
- Parser failures are recorded without crashing the import batch.
- Unit tests cover parsing fallback and skill normalization.

### Dependencies

- Phase 3

---

## Phase 5 - Mentor and Project Normalization

### Goal

Create canonical mentors, projects, prerequisites, preferences, and historical selection signals from imported workbook rows.

### Deliverables

- Mentor normalization and email linking.
- Project normalization from `Mentors-projects` and optional `Probable projects`.
- Prerequisite parsing into skills/technologies.
- Preference/selection fields captured as structured signals when available.

### Definition of Done

- Each valid project row creates or updates a canonical project.
- Mentor names in project rows link to mentor records when possible.
- Unresolvable mentor names create validation warnings.
- Prerequisites are normalized into searchable skill/technology records.

### Dependencies

- Phase 2

---

## Phase 6 - Embedding Service

### Goal

Generate versioned embeddings for canonical candidates and projects.

### Deliverables

- Embedding service interface.
- BGE-M3 implementation.
- Candidate profile serialization format.
- Project serialization format.
- Embedding version metadata.

### Definition of Done

- Canonical candidates and projects can be embedded.
- Embeddings are generated from deterministic serialized text.
- Embedding model and schema versions are stored.
- Unit tests cover serialization format.

### Dependencies

- Phase 4
- Phase 5

---

## Phase 7 - Match Run Orchestration

### Goal

Introduce explicit match runs that execute matching against a selected import batch or candidate/project set.

### Deliverables

- `POST /api/match-runs`
- `GET /api/match-runs/{id}`
- Match-run status transitions.
- Match-run configuration schema.
- Structured failure handling.

### Definition of Done

- A match run can be created and tracked.
- Failed runs record failure reason and logs without losing partial diagnostics.
- Match runs record data versions and scoring configuration.
- Integration tests cover successful and failed run lifecycle.

### Dependencies

- Phase 6

---

## Phase 8 - Reranking and Hybrid Scoring

### Goal

Rank candidates for each project using semantic retrieval, reranking, and transparent score components.

### Deliverables

- pgvector top-K retrieval.
- BGE reranker integration.
- Hybrid scorer with configurable component weights.
- Match result persistence.

### Initial Score Components

- Semantic similarity.
- Reranker relevance.
- Skill/prerequisite overlap.
- Resume evidence coverage.
- Preference/selection signal where available.

### Definition of Done

- Each project receives ranked candidates.
- Component scores and final scores are stored.
- Scoring formula has unit tests with fixed expected values.
- Integration tests verify candidate ranking output shape.

### Dependencies

- Phase 7

---

## Phase 9 - Match Explanations

### Goal

Generate source-grounded plain-language explanations for match results through the centralized generation layer.

### Deliverables

- `ai/generation/match_explanation.py`
- Prompt template for match explanations.
- Deterministic fallback explanation.
- Explanation persistence linked to match results.

### Definition of Done

- Every returned match result has a non-empty explanation.
- LLM failures degrade to deterministic fallback text.
- Explanations distinguish source facts from inferred fit.
- Unit tests cover prompt construction and fallback behavior.

### Dependencies

- Phase 8

---

## Phase 10 - Result Export and Review Contract

### Goal

Return match-run results in formats suitable for human review and later external integration.

### Deliverables

- `GET /api/match-runs/{id}/results`
- `GET /api/match-runs/{id}/export.xlsx`
- Versioned JSON result schema.
- XLSX export with one project-centric ranked list.

### Export Content

- Match-run metadata.
- Project details.
- Ranked candidates.
- Component scores.
- Explanation.
- Data quality warnings.

### Definition of Done

- Export is generated from persisted match results.
- JSON and XLSX outputs include the same ranked data.
- Export tests validate schema and essential workbook content.
- Human reviewers can identify why a candidate was ranked.

### Dependencies

- Phase 9

---

# Post-MVP A - Operator UX and Deployment Readiness

## A1 - Complete Operator Review UI

Build the full operator UI for upload, validation issue review, match-run status, result inspection, and export download.

## A2 - Operator Auth and Access Hardening

Add simple operator authentication, audit trails, retention controls, and deployment-safe access rules.

## A3 - External Integration API

Stabilize API contracts for a larger system, including service authentication, idempotency keys, import status callbacks, and result publishing. Deferred until a real integration exists.

---

# Post-MVP B - Quality and Feedback

## B1 - Reviewer Feedback Capture

Capture reviewer accept/reject/edit decisions as structured feedback linked to match results.

## B2 - AI Evaluation Framework

Measure matching quality using Precision@K, Recall@K, NDCG, MRR, and agreement with historical selections.

## B3 - Scoring Calibration

Tune component weights using labeled feedback and cohort outcomes.

---

# Post-MVP C - Portal Features

These are intentionally deferred because the current MVP only needs an operator upload-and-review workflow.

## C1 - Student Experience

Student dashboard, project recommendations, skill gaps, and learning roadmaps.

## C2 - Mentor Experience

Mentor dashboard, candidate review, project editing, and selection actions.

## C3 - Notifications and Chat

Real-time notifications and accepted-match chat.

## C4 - Admin Panel

User/project moderation and system administration.

## C5 - Production Deployment Hardening

Dedicated workers, object storage, full CI/CD, monitoring dashboards, load tests, and disaster recovery planning.

---

## Backlog

| Feature                    | Notes                                                               |
| -------------------------- | ------------------------------------------------------------------- |
| CSV import                 | Add after XLSX contract stabilizes.                                 |
| API-native imports         | Direct JSON payloads from a future external system.                 |
| Object storage             | Required when resume storage moves beyond local/dev.                |
| Celery/RQ workers          | Add when match runs exceed in-process limits.                       |
| Dedicated vector store     | Evaluate only after pgvector latency becomes a measured bottleneck. |
| Learning feasibility score | Add after enough labeled outcomes exist.                            |
| Cohort analytics           | Aggregate gaps and demand by program/cohort.                        |
| Multi-tenant isolation     | Add if deployed across independent institutions.                    |

---

_Update this roadmap when phases are completed, re-scoped, or superseded by an ADR._
