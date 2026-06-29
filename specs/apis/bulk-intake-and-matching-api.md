# Bulk Intake and Matching API

> Status: Approved
> Related feature: `specs/features/2026-06-26-bulk-intake-and-matching/requirements.md`
> Related ADR: `specs/adrs/ADR-0001-standalone-bulk-intake-matching-mvp.md`

---

## Base Paths

| Domain          | Base Path             |
| --------------- | --------------------- |
| Import batches  | `/api/import-batches` |
| Candidates      | `/api/candidates`     |
| Projects        | `/api/projects`       |
| Mentors         | `/api/mentors`        |
| Recommendations | `/api/matching`       |

---

## Authentication

MVP endpoints are unauthenticated while the app is local/operator-run. Add operator authentication before any public deployment. Service API keys or service JWTs are deferred until a real external integration exists.

Endpoint specs use caller roles for clarity:

| Caller     | Description                                                            |
| ---------- | ---------------------------------------------------------------------- |
| `operator` | Program operator uploading files, reviewing issues, and starting runs. |
| `reviewer` | Human reviewer reading ranked results and explanations.                |
| `student`  | Student candidate uploading resume or querying recommendations.        |
| `mentor`   | Project mentor reviewing candidate recommendation fit.                 |

---

## Common Types

### Import Batch Status

```text
created
parsing
validated
failed
```

### Import File Type

```text
workbook
resume
other
```

### Validation Severity

```text
error
warning
```

---

## Endpoints

### `GET /api/import-batches`

Summary: List all import batches with candidate and project counts.

Auth: Not required in MVP. Caller: `operator`.

### Response - `200 OK`

```json
[
  {
    "id": 1,
    "status": "validated",
    "created_at": "2026-06-26T12:00:00Z",
    "candidate_count": 20,
    "project_count": 8
  }
]
```

---

### `POST /api/import-batches`

Summary: Create a new empty import batch.

Auth: Not required in MVP. Caller: `operator`.

### Response - `201 Created`

```json
{
  "id": 1,
  "status": "created"
}
```

---

### `POST /api/import-batches/{batch_id}/files`

Summary: Attach a workbook or resume file to an import batch and parse it synchronously.

Auth: Not required in MVP. Caller: `operator`.

Content-Type: `multipart/form-data`

### Path Parameters

| Parameter  | Type  | Required | Description      |
| ---------- | ----- | -------- | ---------------- |
| `batch_id` | `int` | Yes      | Import batch id. |

### Form Fields

| Field       | Type   | Required | Description                                       |
| ----------- | ------ | -------- | ------------------------------------------------- |
| `file`      | file   | Yes      | Workbook file (currently only `.xlsx` supported). |
| `file_type` | string | Yes      | `workbook`.                                       |

### Response - `200 OK`

```json
{
  "id": 1,
  "status": "validated",
  "can_proceed": true,
  "sheet_summaries": {
    "Students Info": {
      "total_rows": 20,
      "errors": 0,
      "warnings": 1
    }
  },
  "issues": [
    {
      "sheet_name": "Students Info",
      "row_number": 2,
      "column_name": "Email",
      "code": "MISSING_EMAIL",
      "severity": "warning",
      "message": "Candidate email is missing.",
      "blocking": false
    }
  ]
}
```

---

### `GET /api/candidates`

Summary: List all staged candidates in the system.

Auth: Not required in MVP. Caller: `operator` or `student`.

### Query Parameters

| Parameter         | Type | Required | Description                  |
| ----------------- | ---- | -------- | ---------------------------- |
| `import_batch_id` | int  | No       | Filter by specific batch ID. |

### Response - `200 OK`

```json
[
  {
    "id": 1,
    "import_batch_id": 1,
    "registration_number": "MDS202504",
    "name": "Agnivesh Chatterjee",
    "email": "silvercarbideagc@gmail.com",
    "phone": "8420725911"
  }
]
```

---

### `GET /api/candidates/{id}`

Summary: Fetch specific candidate details and parsed skills.

Auth: Not required in MVP. Caller: `operator`.

### Response - `200 OK`

```json
{
  "id": 1,
  "registration_number": "MDS202504",
  "name": "Agnivesh Chatterjee",
  "email": "silvercarbideagc@gmail.com",
  "phone": "8420725911",
  "skills": ["Python", "Computer Vision", "Shell", "Docker"],
  "has_resume": true
}
```

---

### `GET /api/projects`

Summary: List all staging projects.

Auth: Not required in MVP. Caller: `operator` or `mentor`.

### Query Parameters

| Parameter         | Type | Required | Description                  |
| ----------------- | ---- | -------- | ---------------------------- |
| `import_batch_id` | int  | No       | Filter by specific batch ID. |

### Response - `200 OK`

```json
[
  {
    "id": 1,
    "import_batch_id": 1,
    "title": "Multimodel AI Agents",
    "mentor_name": "Prasun Agarwal",
    "has_abstract": true
  }
]
```

---

### `GET /api/projects/{id}`

Summary: Fetch specific project details.

---

### `GET /api/mentors`

Summary: List all staging mentors and their linked projects.

Auth: Not required in MVP. Caller: `operator`.

---

### `GET /api/mentors/{id}`

Summary: Fetch specific mentor details.

---

### `POST /api/matching/llm-preview`

Summary: Test the configured LLM provider without running full matching.

Auth: Not required in MVP. Caller: `operator`.

---

### `GET /api/matching/student-recommendations/{registration_number}`

Summary: Get project recommendations for an existing imported student using their registration number.

Auth: Not required in MVP. Caller: `student` or `operator`.

### Path Parameters

| Parameter             | Type   | Required | Description                     |
| --------------------- | ------ | -------- | ------------------------------- |
| `registration_number` | string | Yes      | Staged candidate registration # |

### Response - `200 OK`

```json
{
  "candidate_name": "Agnivesh Chatterjee",
  "registration_number": "MDS202504",
  "recommendations": [
    {
      "rank": 1,
      "project_id": 1,
      "project_title": "Multimodel AI Agents",
      "mentor_name": "Prasun Agarwal",
      "final_score": 0.87,
      "score_components": {
        "embedding_similarity": 0.82,
        "prerequisite_overlap": 0.8,
        "resume_experience": 0.75,
        "github_score": 0.9,
        "coding_profile_score": 0.85,
        "achievements_score": 0.7,
        "llm_fit_score": 0.8
      },
      "explanation": "You are a strong fit for this project due to your background in Python, PyTorch, and Computer Vision."
    }
  ]
}
```

---

### `POST /api/matching/student-recommendations`

Summary: Upload a student resume PDF to parse it in-memory on-the-fly and fetch matching projects.

Auth: Not required in MVP. Caller: `student`.

Content-Type: `multipart/form-data`

### Form Fields

| Field              | Type   | Required | Description                                 |
| ------------------ | ------ | -------- | ------------------------------------------- |
| `resume`           | file   | Yes      | PDF file of candidate resume.               |
| `preferred_topics` | string | No       | Optional comma-separated interest keywords. |

---

### `GET /api/matching/project-recommendations/{project_id}`

Summary: Get recommended student candidates for a specific project.

Auth: Not required in MVP. Caller: `mentor` or `operator`.

### Path Parameters

| Parameter    | Type  | Required | Description         |
| ------------ | ----- | -------- | ------------------- |
| `project_id` | `int` | Yes      | Staging project ID. |

---

### `GET /api/matching/batch-scores/{batch_id}`

Summary: Return deterministic (no-LLM) scores for every student×project pair in a batch. Scores are computed and persisted (cached in the database).

Auth: Not required in MVP. Caller: `operator`.

### Query Parameters

| Parameter | Type | Required | Description                                      |
| --------- | ---- | -------- | ------------------------------------------------ |
| `force`   | bool | No       | Pass `true` to clear cache and recompute matrix. |

---

## Deferred API Questions

| Question                                                              | Required Before         | Status                                              |
| --------------------------------------------------------------------- | ----------------------- | --------------------------------------------------- |
| Service API key vs service JWT?                                       | External integration    | Deferred                                            |
| Should result export be generated on demand or cached as an artifact? | Phase 5 completion      | Deferred (CSV/XLSX generation not yet implemented). |
| Should reviewer result edits be accepted in MVP?                      | Post-MVP feedback phase | Deferred                                            |

---

_API spec version 0.3 - updated for current deterministic matrix implementation._
