# ProjectMatchAI - Implementation Roadmap

> Constitution Document - Version 5.0 - June 2026
> This roadmap reflects the simplified in-memory ingest and symmetrical matching recommendation architecture for the standalone upload-and-review MVP.

---

## Guiding Principles

- The MVP validates upload, import, matching, explanation, and result review.
- Every phase produces a reviewable artifact.
- Every feature starts with a spec under `specs/features/`.
- Architecture decisions with meaningful trade-offs require ADRs under `specs/adrs/`.
- Tests are part of every phase's Definition of Done.
- Resumes are parsed entirely in-memory; no raw PDF files are stored on disk.
- Symmetrical recommendation endpoints serve both students (by registration number or resume upload) and mentors (by project ID).

---

## Tier Overview

```text
MVP (Phases 0-5)
  Proves: messy candidate/project data can be imported, normalized in-memory, matched, explained, and exported.

Post-MVP A - Operator UX and Deployment Readiness
  Adds: complete review UI, operator auth, deployment hardening, and optional external API contracts.

Post-MVP B - Quality and Feedback
  Adds: reviewer feedback loops, AI evaluation, scoring iteration, and outcome analytics.

Post-MVP C - Portal and Integration Features
  Adds: student/mentor dashboards, roadmaps, chat, notifications, and admin features only if needed.
```

---

## Phase Summary

| Phase   | Name                                         | Status      |
| ------- | -------------------------------------------- | ----------- |
| Phase 0 | Project Setup                                | Completed   |
| Phase 1 | Data Model                                   | Completed   |
| Phase 2 | Bulk Workbook Import                         | Completed   |
| Phase 3 | In-Memory Ingest & Profile Normalization     | Completed   |
| Phase 4 | Symmetrical Matching & Recommendation APIs   | Completed   |
| Phase 5 | Cohort Match Run & Export                    | Completed   |
| Phase 6 | Deterministic Profile & Code Quality scoring | In Progress |

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

# MVP - Phases 0-5

## MVP Goal

A program operator can provide a workbook with student/candidate and project rows.
ProjectMatchAI can then:

- Validate the imported data and extract Google Drive resume links.
- Programmatically download and parse resumes in-memory (no local PDF storage).
- Normalize candidates, mentors, projects, skills, and prerequisites.
- Provide symmetrical recommendation APIs for students (by registration or resume upload) and mentors (by project ID).
- Run explicit match jobs for the entire cohort.
- Produce ranked recommendations per project with score breakdowns and explanations.
- Export results as JSON and XLSX.

---

## Phase 0 - Project Setup

### Goal

Establish a runnable monorepo foundation.

### Status

Completed.

---

## Phase 1 - Data Model

### Goal

Create the normalized relational schema required for import batches, canonical records, match runs, match results, and auditability.

### Status

Completed.

---

## Phase 2 - Bulk Workbook Import

### Goal

Import workbook data into typed staging records with explicit validation issues.

### Status

Completed.

---

## Phase 3 - In-Memory Ingest & Profile Normalization

### Goal

Link candidate records to Google Drive resumes, parse PDFs in-memory without saving them to disk, normalize candidates, mentors, projects, and prerequisites into canonical registries, and expose read discoverability endpoints.

### Deliverables

- Google Drive link extraction in `workbook_parser.py` (Row 25 cell hyperlink) and metadata row skipping (Rows 24-25).
- In-memory PDF downloader and parser (PyMuPDF) integration.
- Staging of candidate name, contact, skills, and profile details directly to the database.
- Normalization of projects, mentors, email links, and prerequisites.
- Discoverability endpoints:
  - `GET /api/candidates` (list and filter candidates).
  - `GET /api/candidates/{id}` (fetch candidate details).
  - `GET /api/projects` (list and filter projects).
  - `GET /api/projects/{id}` (fetch project details).

### Definition of Done

- Import parser correctly extracts the Google Drive resumes link from `pro.xlsx` without errors.
- Resumes are fetched, parsed in-memory, and candidate profiles are successfully created.
- No resume PDF files are stored on disk.
- Candidates and projects list and detail routes return correct database records.
- Unit and integration tests cover in-memory parsing and CRUD endpoints.

### Dependencies

- Phase 2

---

## Phase 4 - Symmetrical Matching & Recommendation APIs

### Goal

Generate embeddings for candidates and projects, retrieval using pgvector, and build symmetrical student and mentor matching recommendation APIs with qualitative LLM reasoning.

### Status

Completed.

### Deliverables

- Candidate and project serialization + embedding service integration (BGE-M3 or configured API).
- pgvector semantic retrieval.
- Hybrid scoring pipeline (semantic similarity, adjacent skills, candidate preferences boost).
- Symmetrical recommendation routers:
  - `GET /api/matching/student-recommendations/{registration_number}` (retrieve matches for existing student).
  - `POST /api/matching/student-recommendations` (accept resume PDF, parse in-memory, match on-the-fly for new student).
  - `GET /api/matching/project-recommendations/{project_id}` (retrieve student matches for a specific project).
- Qualitative LLM evaluation prompts and deterministic score-based fallback explanations.

### Definition of Done

- Students can query project recommendations by registration number or by uploading a resume.
- Mentors can query candidate recommendations by project ID.
- Recommendations return ranked lists, score breakdowns, and human-like explanations.
- Unit tests verify preference boosts and LLM fallback logic.

### Dependencies

- Phase 3

---

## Phase 5 - Cohort Match Run & Export

### Goal

Run explicit, cohort-wide deterministic matrix score generation and expose a BatchScoreMatrix UI, with export capabilities deferred.

### Status

Completed (Matrix generation & UI), Exports Deferred.

### Deliverables

- Batch Score Matrix execution endpoint (`GET /api/matching/batch-scores/{batch_id}`).
- Deterministic result persistence (`batch_pair_scores` table).
- BatchScoreMatrix UI component in frontend.

### Definition of Done

- Batch score matrix is generated and cached deterministically without LLM.
- Matrix UI renders heatmaps of student vs. project fit.

### Dependencies

- Phase 4

---

## Phase 6 - Deterministic Profile & Code Quality Scoring

### Goal

Incorporate deterministic developer metrics (GitHub, LeetCode, Codeforces, Kaggle, Google Scholar) and achievements into the candidate scoring pipeline, reducing subjective LLM scoring to 5% and using the LLM for qualitative fit explanation synthesis. Check code quality of candidate repositories and ping live links for functionality via an automated Antigravity CLI module.

### Status

In Progress.

### Deliverables

- Profile parser to extract URL handles from candidate resumes.
- Scraper/enrichment service supporting GitHub, LeetCode, Codeforces, and Scholar metrics, with mock fallbacks.
- Antigravity CLI repository inspector checking code quality, readme/license hygiene, and live website status.
- Final scoring weights update: GitHub (30%), LeetCode/Codeforces (20%), Scholar/Achievements (10%), LLM evaluation (5%), Embedding Similarity (10%), Prerequisite Overlap (15%), Resume Experience (10%).

### Definition of Done

- Resume parser correctly extracts social handles.
- Social handle crawlers fetch stats and save to Postgres Candidate profiles.
- Score components output deterministic metrics instead of subjective LLM metrics.
- Symmetrical recommendations output valid explanation JSONs utilizing only qualitative synthesis.

### Dependencies

- Phase 5

---

# Post-MVP & Backlog

Refer to previous specs and Backlog for details on UI operator consolidation, feedback loop systems, and vector search fine-tuning.
