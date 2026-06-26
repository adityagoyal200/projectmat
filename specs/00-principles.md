# ProjectMatchAI - Engineering Principles

> Constitution Document - Version 2.0 - June 2026
> This document defines how we build ProjectMatchAI. Where `mission.md` defines what the system is for, this file defines the engineering constraints every roadmap, ADR, feature spec, code change, and review must satisfy.

---

## Why This Document Exists

ProjectMatchAI is a standalone upload-and-review app for the current MVP. Its job is to reliably ingest candidate, resume, mentor, and project data; produce explainable match recommendations; and show or export auditable outputs for human review.

The architecture should remain API-first so it can plug into a larger program-management system later, but the MVP should not build integration complexity before it is needed.

These principles prevent two failure modes:

1. Over-engineering: building platform features before the matching hypothesis is validated.
2. Under-engineering: treating ingestion, AI scoring, privacy, and explainability as scripts instead of production system boundaries.

When principles conflict with convenience, the principle wins.

---

## Core Principles

### 1. YAGNI - You Aren't Gonna Need It

Build only what is required for the current roadmap phase.

In practice:

- Do not build standalone student, mentor, chat, admin, or notification experiences until the matching subsystem requires them.
- Do not add multi-tenant, task-queue, or enterprise workflow infrastructure before the MVP match-run lifecycle proves it needs them.
- Keep post-MVP ideas in the roadmap or backlog, not in speculative code paths.

### 2. KISS - Keep It Simple

The simplest solution that satisfies the current requirements is the correct solution.

In practice:

- Prefer a typed import pipeline over ad hoc spreadsheet parsing scattered through services.
- Prefer one explicit match-run workflow over many hidden triggers.
- Prefer boring, observable infrastructure over clever automation.

### 3. Backend Boundary First

ProjectMatchAI must have a clear boundary between the frontend review surface and backend business logic.

In practice:

- The frontend uploads files, shows validation issues, starts match runs, and displays results.
- The backend owns Excel parsing, validation, normalization, resume parsing, AI enrichment, matching, explanations, persistence, and export.
- Future upstream integrations must use the same backend contracts instead of moving parsing or matching into the frontend.
- Every file input and result output contract must be documented before implementation.

### 4. Feature First

Ship a working matching feature before optimizing it.

The MVP exists to answer one question:

> Can ProjectMatchAI produce better, faster, explainable student-project match recommendations from messy cohort data than manual spreadsheet review?

Anything that does not directly support that question is deferred.

### 5. AI Agnostic

Business logic must not depend on a specific LLM, embedding model, OCR engine, or resume parser.

In practice:

- All generation goes through `ai/generation/`.
- Embedding calls go through an embedding service interface.
- OCR and document parsing are isolated behind parser interfaces.
- Provider selection is configuration, not business logic.

### 6. SOLID

Brief application to this codebase:

| Principle             | Application                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------ |
| Single Responsibility | Import parsers parse files; validators validate; services orchestrate; repositories persist.           |
| Open/Closed           | New import formats, AI providers, or scoring signals can be added without rewriting matching services. |
| Liskov Substitution   | Provider implementations must be interchangeable behind their interfaces.                              |
| Interface Segregation | Resume parsing, spreadsheet parsing, embeddings, reranking, and generation have narrow contracts.      |
| Dependency Inversion  | Services depend on interfaces and repositories, not concrete vendors or file formats.                  |

### 7. Modularity

Every feature is a cohesive module with explicit boundaries.

Structure rules:

- Feature modules own their router, service, repository, schemas, and models.
- Shared AI code lives under `ai/` and has no knowledge of FastAPI routes or UI concerns.
- Import, candidate, mentor, project, matching, export, and evaluation logic must not reach into each other's internals.

Folder law:

> If a feature folder cannot be removed without breaking unrelated feature folders, the boundary is wrong.

### 8. Testing First

A feature is not done until its tests are written and passing.

Minimum expectations:

- Unit tests for parsers, validators, normalizers, scoring formulas, and AI fallback behavior.
- Integration tests for import endpoints, match-run lifecycle, persistence, and export.
- Fixture-based tests using representative messy workbook rows and resumes.
- AI evaluation metrics once historical selections or reviewer labels exist.

### 9. Documentation First

The `specs/` directory is the source of truth.

In practice:

- Every feature follows the templates in `specs/templates/`.
- Architecture trade-offs are recorded as ADRs.
- Import contracts, validation rules, and output contracts are documented before implementation.
- If the spec and implementation disagree, update the spec deliberately before changing code.

### 10. No Premature Optimization

Optimize only when evidence shows a bottleneck.

In practice:

- Do not introduce Celery, Redis, Kubernetes, or a dedicated vector database before measured need.
- Start with PostgreSQL and pgvector for MVP-scale candidate sets.
- Start with an explicit match-run status model before adding distributed job orchestration.

### 11. Explicit Over Implicit

Hidden behavior is a production risk.

In practice:

- Import validation must produce explicit warnings and errors.
- Match runs must be versioned and reproducible.
- Score components must be visible in outputs.
- Environment variables live in `app/config.py`, not scattered through the codebase.
- API request and response models must be typed.

---

## Engineering Decision Checklist

Use this checklist before approving an architecture or implementation:

```text
[ ] Is the requirement in the current roadmap phase?
[ ] Is the frontend/backend boundary explicit?
[ ] Is this the simplest design that satisfies the current phase?
[ ] Are AI providers, parsers, and models replaceable?
[ ] Are responsibilities separated into cohesive modules?
[ ] Is the input/output contract documented?
[ ] Are failure states observable and testable?
[ ] Are unit and integration tests specified?
[ ] Is there evidence for any optimization being introduced?
```

---

_This document should be revised only when the project enters a materially different operating model._
