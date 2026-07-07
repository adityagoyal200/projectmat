# Phase 4 - Symmetrical Matching & Recommendation APIs - Requirements

## Status

`[x] Done`

## Author

Antigravity

## Date

2026-06-28

## Related Phase

Phase 4 - Symmetrical Matching & Recommendation APIs

## 1. Problem Statement

Program operators and mentors need to match students to projects using more than simple keyword filters. The matching process needs to be:

1. **Symmetrical**: Allowing students to see project matches (via registration ID or resume upload) and mentors/projects to find students.
2. **Hybrid & Multi-signal**: Combining vector embeddings (semantic context), deterministic skills/prerequisite overlap, resume evidence, and optional developer metrics.
3. **Explainable**: Providing human-readable explanations of why a student matches a project, with fallback logic when LLMs are offline or disabled.

## 2. Proposed Solution

1. **Text Serialization & Vectorization**: Serialize candidate profiles and project descriptions, generate embeddings using BAAI BGE-M3, and store them in PostgreSQL with pgvector.
2. **Retrieve-and-Rerank Pipeline**:
   - Retrieve candidate pools using cosine distance.
   - Run a hybrid scoring formula combining embeddings, prerequisite alignment, resume experience depth, and preference markers.
   - Run optional LLM evaluation for top-K candidates to refine scores and generate qualitative justifications.
3. **Recommendation Routers**:
   - `GET /api/matching/student-recommendations/{registration_number}`: Symmetrical project recommendation.
   - `POST /api/matching/student-recommendations`: Accept a resume PDF, parse in-memory on-the-fly, and return immediate project recommendations.
   - `GET /api/matching/project-recommendations/{project_id}`: Symmetrical student recommendations.

## 3. User Stories

- As a **Student**, I want to **query project recommendations using my registration number**, so that **I can discover projects that fit my profile**.
- As a **Student**, I want to **upload my resume PDF to search on-the-fly**, so that **I can get instant project recommendations without being pre-imported**.
- As a **Mentor**, I want to **view recommended students for my project ID**, so that **I can find the best matching candidates**.
- As an **Operator**, I want to **verify the LLM reasoning pipeline with a preview endpoint**, so that **I can ensure prompt and model configurations work**.

## 4. Input and Output Contracts

### Inputs

- Candidate registration number.
- Uploaded resume PDF.
- Target project ID.

### Outputs

- Ranked lists of matches with final score, component score breakdowns, and textual explanation logs.

## 5. Scope

### In Scope

- pgvector semantic retrieval and cosine distance.
- Hybrid scoring formula coordinating embed score, prerequisite score, resume score, and preference signal.
- Recommendation APIs for candidates (by registration or resume upload) and projects.
- Qualitative LLM prompts and deterministic fallback explanations when LLMs fail.

### Out of Scope

- Interactive cohort editing UI (handled under Phase 5 review matrix).

## 6. API Design

| Method | Path                                                          | Description                                          | Roles                 |
| ------ | ------------------------------------------------------------- | ---------------------------------------------------- | --------------------- |
| `POST` | `/api/matching/llm-preview`                                   | Preview raw prompts against the active LLM.          | `operator`            |
| `GET`  | `/api/matching/student-recommendations/{registration_number}` | Get project recommendations for an existing student. | `student`, `operator` |
| `POST` | `/api/matching/student-recommendations`                       | On-the-fly project recommendation via PDF upload.    | `student`             |
| `GET`  | `/api/matching/project-recommendations/{project_id}`          | Get recommended students for a specific project.     | `mentor`, `operator`  |

## 7. Definition of Done

- [x] Symmetrical student and project recommendation endpoints are operational.
- [x] On-the-fly PDF resume upload endpoint returns ranked matches synchronously.
- [x] Embeddings are correctly stored and retrieved via pgvector.
- [x] Qualitative LLM justifications are generated, falling back to structured template explanations on failure.
- [x] Comprehensive test coverage is established for scoring and routers.
