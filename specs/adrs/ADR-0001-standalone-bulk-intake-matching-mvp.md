# ADR-0001 - Standalone Bulk Intake and Matching MVP

## Status

`[x] Accepted`

## Date

2026-06-26

## Authors

ProjectMatchAI Engineering Team

## Deciders

Product owner and technical lead

---

## Context

ProjectMatchAI was originally specified as a full student/mentor platform with registration, dashboards, project creation, chat, feedback, admin, and AI matching.

The requirement has changed. ProjectMatchAI should now be a standalone upload-and-review app for the MVP. A program operator uploads candidate/student data from spreadsheets and optional resume PDFs. The operator also uploads mentor and project data from workbooks like the reference file `Copy of summer-internship-2026 - Alumni Mentorship Projects.xlsx`.

The reference workbook contains these sheets:

| Sheet               | Observed purpose                                                                        |
| ------------------- | --------------------------------------------------------------------------------------- |
| `Students Info`     | Candidate identity, registration number, email, phone, resume file name.                |
| `Mentors info`      | Mentor name and email.                                                                  |
| `Mentors-projects`  | Mentor profile, project title, abstract, prerequisites, preferences, selected students. |
| `Probable projects` | Optional project ideas with author and topic.                                           |

The system needs to produce AI-assisted matches and show them for human review. It should not own unrelated product workflows such as student accounts, mentor accounts, chat, notifications, or automatic final allocation. The backend should remain API-first so future integration with a larger platform is possible without rewriting the core pipeline.

---

We will implement ProjectMatchAI as a modular monolith standalone app with explicit bulk intake, normalization, batch-score-generation, explanation, review, and export boundaries. MVP will ingest workbook and resume inputs, validate and normalize them into canonical records, generate deterministic batch score matrices enriched by external developer profiles (GitHub, LeetCode, Codeforces, Google Scholar) and achievements. The scoring weights are structured to minimize LLM subjective scoring down to 5%, with 30% assigned to GitHub (verified via repository and code quality checks) and 10% to academic achievements. Student/mentor portal features and external integration are deferred until the upload-and-review workflow is validated.

---

## Rationale

Primary reasons:

1. Frontend/backend boundary matches the new requirement: the frontend should only upload files, trigger work, and show results; the backend should own parsing, validation, matching, explanations, and export.
2. Bulk intake is the real risk: spreadsheet data is messy, so import validation and normalization must be first-class production features rather than temporary scripts.
3. Batch scores need auditability: recommendations must be reproducible, explainable, and tied to exact input, model, and scoring versions.
4. A modular monolith is enough for MVP: separate services, task queues, and vector databases add operational complexity before scale proves they are needed.
5. Portal features are not on the critical path: accounts, chat, notifications, and admin screens do not validate whether AI matching works.

---

## Alternatives Considered

### Option A: Keep the Standalone Platform Roadmap

Description: Continue building authentication, student profiles, mentor dashboards, chat, feedback, admin, and then matching.

Pros:

- Complete product experience.
- Clear user-facing workflows.

Cons:

- Builds many features not required for the upload-and-review MVP.
- Delays validation of the core matching hypothesis.
- Increases scope and maintenance surface.

Why rejected:

The changed requirement makes upload-and-review matching the immediate product. Building a full portal first violates YAGNI and delays the highest-risk workflow.

### Option B: Notebook or Script-Based Matching Pipeline

Description: Write a one-off script to read Excel files and resumes, call AI models, and write output spreadsheets.

Pros:

- Fastest short-term path.
- Useful for exploratory experiments.

Cons:

- Poor testability.
- Poor auditability.
- Hard to integrate with upstream systems.
- Easy to accumulate hidden data-cleaning behavior.

Why rejected:

The product goal is a production-quality AI platform. A script can inform fixtures or prototypes, but it cannot be the architecture.

### Option C: Distributed Microservices from Day One

Description: Split ingestion, resume parsing, embeddings, matching, generation, and export into separate services with a queue.

Pros:

- Strong independent scaling boundaries.
- Good fit for large workloads.

Cons:

- More deployments, queues, observability, retries, and failure modes.
- Slower MVP development.
- Unjustified before real workload measurements.

Why rejected:

Current cohort-sized workbooks do not justify the complexity. The modular monolith can preserve boundaries and move to workers later.

### Option D: Recommended - Modular Monolith Subsystem

Description: Build one backend with clean feature modules and explicit match-run lifecycle.

Pros:

- Fast enough for MVP.
- Testable and observable.
- Clean frontend/backend boundary.
- Easy to evolve toward workers or services later.

Cons:

- Long-running jobs need careful status tracking.
- Scaling is limited until worker extraction happens.

Why selected:

It best satisfies KISS, YAGNI, Clean Architecture, AI Agnostic Design, Documentation First, and Testing First.

---

## Trade-offs Accepted

By choosing this approach, we accept:

- In-process compute limits: MVP batch score matrix generation executes large cross-products and may need pagination or worker timeouts. Mitigation: persist deterministic pairs in `batch_pair_scores` and serve from cache, making worker extraction a future-compatible change.
- Less portal polish initially: students and mentors do not directly interact with ProjectMatchAI in MVP. Mitigation: the operator review UI and exports support human review.
- More upfront schema design: import and match-run auditability require more tables than a simple script. Mitigation: tables map directly to production needs and avoid speculative portal models.

---

## Consequences

Positive:

- MVP focuses on the highest-risk and highest-value capability: AI matching from messy real data.
- A future platform can integrate without rewriting import, matching, scoring, or explanation logic.
- Import validation, scoring, explanations, and exports become testable product features.

Negative:

- Existing roadmap phases for auth, dashboards, chat, and admin are superseded or deferred.
- Some previous docs and assumptions must be rewritten before implementation continues.

Follow-up actions:

- [x] Approve or revise this ADR.
- [ ] Approve the bulk intake and matching feature specification.
- [ ] Implement Phase 1 data model after approval.
- [ ] Create fixture workbooks and resume samples for validation tests.

---

## Industry Practice

Startups typically begin with a modular monolith or well-structured service that imports spreadsheets, runs matching, and exports reviewable outputs before investing in a full portal.

Mid-sized SaaS companies usually add stable APIs, background workers, review UIs, audit logs, and feedback loops once the workflow is validated.

Large technology companies typically split ingestion, feature extraction, ranking, evaluation, and serving into separate services with queues, model registries, offline/online feature stores, and continuous evaluation. That is appropriate later, not for this MVP.

---

## Revisit Criteria

This decision should be revisited if:

- Match runs regularly exceed safe in-process worker limits.
- A larger system asks ProjectMatchAI to become the source of truth for users, selections, or communications.
- Multiple institutions require hard tenant isolation.
- Candidate/project volume makes pgvector latency exceed agreed SLAs.
- Reviewer feedback data is large enough to justify a separate ranking/evaluation pipeline.

---

## References

- `specs/00-principles.md`
- `specs/mission.md`
- `specs/tech-stack.md`
- `specs/roadmap.md`
- `specs/features/2026-06-26-bulk-intake-and-matching/requirements.md`

---

_ADRs are immutable after acceptance. If this decision changes, create a new ADR that supersedes this one._
