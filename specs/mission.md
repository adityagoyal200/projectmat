# ProjectMatchAI - Mission

> Constitution Document - Version 2.0 - June 2026
> This document defines what ProjectMatchAI is building and why. It is a living source of truth and must be updated deliberately when product scope changes.

---

## 1. Project Vision

ProjectMatchAI is an AI-powered standalone upload-and-review app for internship, mentorship, research, and project-based learning programs.

It receives structured and semi-structured data from operator uploads: student/candidate spreadsheets, resume files, mentor records, project descriptions, prerequisites, preferences, and historical selection signals. It normalizes that data, enriches candidate and project profiles, runs explainable AI matching, and shows or exports ranked recommendations for human review.

The backend remains API-first so ProjectMatchAI can later become part of a larger system without rewriting the core import and matching pipeline.

---

## 2. Problem Statement

### For Program Operators

Program teams often manage candidate lists, resume folders, mentor details, project descriptions, preferences, and final selections across disconnected spreadsheets. Matching students to projects becomes slow, subjective, and hard to audit. Small inconsistencies, missing fields, and ambiguous prerequisites make manual review even more fragile.

### For Mentors

Mentors need candidates who fit both the project requirements and the learning context. Manually reading every resume and spreadsheet row is time-consuming, and simple keyword filters miss candidates with strong adjacent skills or fast learning potential.

### For Students and Candidates

Students are often evaluated on visible keywords rather than growth potential, project fit, or evidence spread across resumes and program records. They benefit when recommendations are explainable and when final decisions remain human-reviewed.

### For Future Integrations

The same backend should later support an upstream platform that submits candidate/project data and consumes match results. That integration is not required for the MVP.

---

## 3. Goals

| #   | Goal                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ |
| G1  | Import candidate/student data from spreadsheets and optional resume files or file references.                                        |
| G2  | Import mentor and project data from spreadsheets or future API payloads.                                                             |
| G3  | Normalize messy source data into canonical candidates, mentors, projects, skills, technologies, and prerequisites.                   |
| G4  | Match candidates to projects based on skills, semantic alignment, prerequisites, preferences, resume evidence, and growth potential. |
| G5  | Provide explainable AI recommendations with score breakdowns and source-grounded rationale.                                          |
| G6  | Produce auditable match-run outputs that can be reviewed by humans or consumed by an upstream system.                                |
| G7  | Keep AI providers, embedding models, OCR engines, and parsers replaceable.                                                           |
| G8  | Preserve privacy and consent boundaries for resumes, personal data, and generated embeddings.                                        |

---

## 4. Non-Goals

| #   | Non-Goal                                                                                                              |
| --- | --------------------------------------------------------------------------------------------------------------------- |
| NG1 | ProjectMatchAI is not the system of record for enrollment, official acceptance, or program operations.                |
| NG2 | ProjectMatchAI does not make final allocation decisions automatically. Humans approve final matches.                  |
| NG3 | ProjectMatchAI is not a job board, freelance marketplace, LMS, or social network.                                     |
| NG4 | MVP does not require student registration, mentor accounts, chat, notifications, or admin moderation.                 |
| NG5 | MVP does not require a distributed task queue, multi-tenant architecture, or dedicated vector database.               |
| NG6 | The system will not store or train on private candidate data without explicit consent and documented retention rules. |

---

## 5. Target Users

### Program Operators

- Upload or send cohort spreadsheets, mentor/project spreadsheets, and resume bundles.
- Review validation errors and warnings.
- Trigger match runs and export ranked recommendations.

### Mentors and Reviewers

- Review ranked candidates for their projects.
- Read score breakdowns and explanations.
- Make final selections outside or inside the larger platform, depending on integration phase.

### Students and Candidates

- Provide resumes and profile data through the larger system.
- Benefit from fairer matching and, in later phases, receive learning gap feedback.

### Future Integration Consumers

- Upstream product services that may later send candidate/project data to ProjectMatchAI.
- Downstream review or allocation workflows that may later consume match-run results.

---

## 6. Core Product Principles

### P1 - Humans Decide, AI Assists

The AI system produces ranked recommendations, warnings, and explanations. It never performs final project allocation without human approval.

### P2 - Explainability Is Non-Negotiable

Every recommendation must include a plain-language explanation and a score breakdown. Black-box ranking is unacceptable.

### P3 - Growth Over Credential

The system should surface candidates who can plausibly grow into a project, not only candidates who already list exact keywords.

### P4 - Source-Grounded Matching

Recommendations must be grounded in imported records, resume evidence, project prerequisites, and documented scoring signals. The system must distinguish known facts from AI inference.

### P5 - Validation Before Matching

Messy import data is expected. The system must validate and report missing fields, duplicate candidates, unknown resume files, ambiguous mentors, empty prerequisites, and malformed contact data before matching.

### P6 - Privacy and Consent First

Candidate profiles, resumes, embeddings, and generated explanations are personal data. Retention, deletion, and auditability are first-class requirements.

---

## 7. Engineering Principles

### E1 - Clean Architecture

Separate API, service, repository, parser, AI, and export concerns. No business logic in route handlers. No database access outside repositories.

### E2 - Feature-Based Structure

Organize backend and frontend code by domain: imports, candidates, mentors, projects, matching, exports, evaluation, and review.

### E3 - Modular AI Services

Embedding, reranking, generation, resume parsing, OCR, and extraction are replaceable services behind explicit interfaces.

### E4 - Integration Contracts

Every inbound file/API contract and outbound result contract is documented and versioned.

### E5 - Test at Every Phase

Unit, integration, and fixture-based validation tests are required for every phase.

### E6 - Incremental and Reviewable

Each phase must produce a working artifact that can be reviewed independently.

### E7 - Observable Systems

Import failures, parsing errors, model failures, match-run status, latency, and fallback behavior must be logged with structured context.

---

## 8. AI Principles

### AI1 - Abstract Provider Interfaces

All model calls route through provider interfaces selected by configuration.

### AI2 - Structured Ingestion First

Spreadsheet and resume inputs are converted into typed canonical schemas before embedding, scoring, or generation.

### AI3 - Semantic Search plus Reranking

Candidate-project retrieval uses embeddings for broad recall and reranking for precision.

### AI4 - Hybrid Scoring

Final ranking combines semantic similarity, reranker relevance, skill/prerequisite overlap, resume evidence, preference signals, and later mentor feedback.

### AI5 - Grounded Explanations

LLM explanations must be generated from structured candidate/project context and score components. If the LLM fails, deterministic fallback explanations must still be returned.

### AI6 - Versioned Match Runs

Every match run records data import version, schema version, scoring version, model versions, and configuration used to generate results.

### AI7 - Embeddings Are Versioned

Every embedding records model name, model version, schema version, source record version, and generated timestamp.

---

## 9. MVP Success Criteria

| Criterion                                                                                      | Target    |
| ---------------------------------------------------------------------------------------------- | --------- |
| A program operator can import a workbook with students, mentors, and projects.                 | Working   |
| The system validates missing and inconsistent input data before matching.                      | Working   |
| Resume file references can be linked to candidate records and parsed when files are available. | Working   |
| Projects and prerequisites are normalized into canonical records.                              | Working   |
| A match run generates ranked candidates per project with component scores.                     | Working   |
| Each recommendation includes a source-grounded explanation.                                    | Present   |
| Results can be exported for human review or returned via API.                                  | Working   |
| AI providers and model choices remain replaceable.                                             | Validated |

---

## 10. Future Vision

Near term:

- API-first integration with a larger platform.
- Reviewer UI for validation issues and match-run review.
- Export back to spreadsheet formats used by program teams.

Medium term:

- Mentor feedback loops and AI evaluation datasets.
- Student-facing skill-gap reports and learning recommendations.
- Cohort analytics for program operators.

Long term:

- Multi-institution deployments with privacy-preserving data boundaries.
- Continuous quality evaluation of matching outcomes.
- Open integration API for third-party program management systems.

---

_This document should be reviewed when ProjectMatchAI becomes the source of truth for additional workflows or when external integration becomes part of the active roadmap._
