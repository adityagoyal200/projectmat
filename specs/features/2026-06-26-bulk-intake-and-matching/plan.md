# Implementation Plan: Bulk Intake and Matching

> This plan is not approval to implement production code. It defines the implementation sequence after ADR-0001 and the feature spec are approved.

---

## 1. Architecture Approval

- [ ] Review ADR-0001 with product owner and technical lead.
- [ ] Resolve MVP auth boundary: service API key vs service JWT.
- [ ] Resolve resume storage boundary: upload files vs upstream references.
- [ ] Confirm whether historical `Selected students` should be used as labels only or scoring signal.
- [ ] Approve or revise `requirements.md`.

---

## 2. Data Model Foundation

- [ ] Add SQLAlchemy models for import batches, import files, validation issues, candidates, mentors, projects, match runs, match results, and explanations.
- [ ] Add normalized shared registries for skills and technologies if not already present.
- [ ] Add model relationships and uniqueness constraints.
- [ ] Create Alembic migration.
- [ ] Verify upgrade and downgrade on a fresh database.
- [ ] Add model-level unit tests where relationships or constraints need coverage.

---

## 3. Import File Storage and Registration

- [ ] Add import batch creation service and repository.
- [ ] Add file registration for workbooks and resumes.
- [ ] Validate file extension, MIME type where available, size, checksum, and duplicate file names within a batch.
- [ ] Store files in the configured local development storage path for MVP.
- [ ] Add API endpoints for batch creation, file attach, batch detail, and issue listing.
- [ ] Add integration tests for file registration and invalid file handling.

---

## 4. Workbook Parser

- [ ] Implement parser under `features/imports/parsers/`.
- [ ] Define sheet aliases for:
  - `Students Info`
  - `Mentors info`
  - `Mentors-projects`
  - `Probable projects`
- [ ] Define header aliases for known workbook columns.
- [ ] Preserve source sheet, row number, raw row snapshot, and normalized row fields.
- [ ] Treat optional sheets and columns explicitly.
- [ ] Add fixture workbook tests based on the reference workbook shape.

---

## 5. Validation Rules

- [ ] Implement candidate validation:
  - Missing name.
  - Missing registration number.
  - Duplicate registration number.
  - Invalid email.
  - Phone stored as text.
  - Missing referenced resume file.
- [ ] Implement mentor validation:
  - Missing mentor name.
  - Invalid email.
  - Duplicate mentor ambiguity.
- [ ] Implement project validation:
  - Missing project title.
  - Missing mentor.
  - Mentor name not linkable to mentor info.
  - Empty abstract warning.
  - Empty prerequisites warning.
- [ ] Persist validation issues with severity, code, message, sheet, and row.
- [ ] Add tests for each issue code.

---

## 6. Normalization

- [ ] Normalize candidates from `Students Info`.
- [ ] Normalize candidate contacts.
- [ ] Normalize mentors from `Mentors info` and project rows.
- [ ] Normalize projects from `Mentors-projects`.
- [ ] Normalize prerequisite text into candidate skills, project prerequisites, skills, technologies, or unresolved raw text.
- [ ] Capture existing preferences and selections as source signals.
- [ ] Add idempotency rules so re-parsing the same batch does not duplicate canonical records.
- [ ] Add unit and integration tests.

---

## 7. Resume Intake and Enrichment

- [ ] Link candidate rows to resume files by exact file name first.
- [ ] Add fallback linking by registration number embedded in file name.
- [ ] Parse digital PDFs with PyMuPDF.
- [ ] Add OCR fallback only when digital extraction fails or is below threshold.
- [ ] Convert parsed resume content into structured profile fields.
- [ ] Normalize resume-derived skills and technologies with source metadata.
- [ ] Record parser version, status, confidence, and failure reason.
- [ ] Add tests for success, missing resume, failed parser, and OCR fallback.

---

## 8. Embeddings

- [ ] Define candidate serialization format.
- [ ] Define project serialization format.
- [ ] Implement embedding service interface.
- [ ] Add BGE-M3 provider.
- [ ] Generate and persist candidate/project embeddings with version metadata.
- [ ] Add unit tests for serialization and integration tests for persistence.

---

## 9. Match Run Lifecycle

- [ ] Add match-run create endpoint.
- [ ] Validate batch readiness before matching.
- [ ] Implement status transitions:
  - `queued`
  - `running`
  - `completed`
  - `failed`
  - `cancelled`
- [ ] Persist scoring configuration and model versions.
- [ ] Record structured failure reasons.
- [ ] Add integration tests for successful and failed runs.

---

## 10. Retrieval, Reranking, and Scoring

- [ ] Retrieve candidate pool per project using pgvector.
- [ ] Rerank candidate/project pairs when reranker is available.
- [ ] Implement hybrid scoring:
  - Semantic similarity.
  - Reranker relevance.
  - Skill/prerequisite overlap.
  - Resume evidence coverage.
  - Preference/selection signal.
- [ ] Persist rank and score components.
- [ ] Add fixed-input unit tests for formula behavior.
- [ ] Add integration tests for result ordering and persistence.

---

## 11. Explanation Generation

- [ ] Implement `ai/generation/match_explanation.py`.
- [ ] Add prompt template with candidate facts, project facts, and score components.
- [ ] Add deterministic fallback explanation.
- [ ] Persist explanation method and prompt version.
- [ ] Add tests for prompt construction, provider failure, and non-empty fallback.

---

## 12. Results and Export

- [ ] Add JSON results endpoint.
- [ ] Add XLSX export endpoint.
- [ ] Include project-centric ranked lists.
- [ ] Include match-run metadata, component scores, explanations, and warnings.
- [ ] Ensure export uses persisted results only.
- [ ] Add integration tests for JSON schema and workbook content.

---

## 13. Documentation and Validation

- [ ] Add API specs for import and match-run endpoints.
- [ ] Update README with subsystem MVP workflow once implementation exists.
- [ ] Add fixture data notes for workbook/resume test files.
- [ ] Run unit and integration test suites.
- [ ] Validate feature against `validation.md`.

---

## Implementation Stop Conditions

Stop and return to architecture review if:

- The upstream system requires ProjectMatchAI to own user identity or final allocations.
- Resume files cannot be transferred or referenced under current privacy constraints.
- Workbooks vary so much that the documented input contract is insufficient.
- Match runs require distributed processing before MVP is complete.

---

_This plan should be executed phase by phase after approval._
