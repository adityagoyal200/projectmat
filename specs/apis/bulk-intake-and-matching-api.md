# Bulk Intake and Matching API

> Status: Review
> Related feature: `specs/features/2026-06-26-bulk-intake-and-matching/requirements.md`
> Related ADR: `specs/adrs/ADR-0001-bulk-intake-matching-subsystem.md`

---

## Base Paths

| Domain         | Base Path             |
| -------------- | --------------------- |
| Import batches | `/api/import-batches` |
| Match runs     | `/api/match-runs`     |

## Authentication

MVP auth mode is an open architecture question. The API must support one of:

- Service API key for trusted upstream system calls.
- Service JWT issued by the larger platform.

Until resolved, endpoint specs use caller roles:

| Caller        | Description                                                            |
| ------------- | ---------------------------------------------------------------------- |
| `integration` | Trusted upstream system submitting imports and consuming results.      |
| `operator`    | Program operator uploading files, reviewing issues, and starting runs. |
| `reviewer`    | Human reviewer reading ranked results and explanations.                |

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

### Match Run Status

```text
queued
running
completed
failed
cancelled
```

---

## Endpoints

## `POST /api/import-batches`

Summary: Create a new import batch.

Auth: Required. Caller: `integration` or `operator`.

### Request Body

```json
{
  "source_system": "program-portal",
  "source_reference": "summer-internship-2026",
  "notes": "Alumni mentorship import"
}
```

### Response - `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source_system": "program-portal",
  "source_reference": "summer-internship-2026",
  "status": "created",
  "created_at": "2026-06-26T12:00:00Z"
}
```

### Side Effects

- Creates an `import_batches` record.
- Writes an audit log.

---

## `POST /api/import-batches/{batch_id}/files`

Summary: Attach a workbook or resume file to an import batch.

Auth: Required. Caller: `integration` or `operator`.

Content-Type: `multipart/form-data`

### Path Parameters

| Parameter  | Type   | Required | Description      |
| ---------- | ------ | -------- | ---------------- |
| `batch_id` | `UUID` | Yes      | Import batch id. |

### Form Fields

| Field                   | Type   | Required | Description                                  |
| ----------------------- | ------ | -------- | -------------------------------------------- |
| `file`                  | file   | Yes      | Workbook or resume file.                     |
| `file_type`             | string | Yes      | `workbook`, `resume`, or `other`.            |
| `candidate_external_id` | string | No       | Optional direct resume-to-candidate mapping. |

### Response - `201 Created`

```json
{
  "id": "6fa459ea-ee8a-3ca4-894e-db77e160355e",
  "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "students.xlsx",
  "file_type": "workbook",
  "status": "uploaded",
  "checksum": "sha256:...",
  "created_at": "2026-06-26T12:05:00Z"
}
```

### Error Responses

| Status | Condition                           |
| ------ | ----------------------------------- |
| `400`  | Unsupported file type.              |
| `404`  | Import batch not found.             |
| `413`  | File exceeds configured size limit. |

### Side Effects

- Stores the file in configured storage.
- Creates an `import_files` record.
- Writes an audit log.

---

## `POST /api/import-batches/{batch_id}/parse`

Summary: Parse attached workbooks and create validation issues plus canonical/staged import records.

Auth: Required. Caller: `integration` or `operator`.

### Request Body

```json
{
  "strict": false
}
```

`strict=false` means warnings do not block normalization or later match runs. Errors always block match runs until resolved or explicitly excluded by a future approved workflow.

### Response - `202 Accepted`

```json
{
  "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "parsing",
  "message": "Workbook parsing started"
}
```

### Side Effects

- Starts parsing work in-process for MVP or queues it in a future worker.
- Creates validation issue records.
- Updates import batch status.

---

## `GET /api/import-batches/{batch_id}`

Summary: Fetch import batch status and summary counts.

Auth: Required. Caller: `integration` or `operator`.

### Response - `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "validated",
  "source_system": "program-portal",
  "source_reference": "summer-internship-2026",
  "counts": {
    "files": 4,
    "candidates": 22,
    "mentors": 13,
    "projects": 8,
    "errors": 0,
    "warnings": 6
  },
  "created_at": "2026-06-26T12:00:00Z",
  "completed_at": "2026-06-26T12:08:00Z"
}
```

---

## `GET /api/import-batches/{batch_id}/issues`

Summary: List validation issues for an import batch.

Auth: Required. Caller: `integration` or `operator`.

### Query Parameters

| Parameter   | Type   | Required | Default | Description           |
| ----------- | ------ | -------- | ------- | --------------------- |
| `severity`  | string | No       | all     | `error` or `warning`. |
| `page`      | int    | No       | `1`     | Page number.          |
| `page_size` | int    | No       | `50`    | Max 200.              |

### Response - `200 OK`

```json
{
  "items": [
    {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "severity": "warning",
      "code": "candidate.resume_missing",
      "message": "Candidate references a resume file that was not attached to the batch.",
      "sheet_name": "Students Info",
      "row_number": 3,
      "raw_value": "Ahana_Sen_MDS202505.pdf"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

---

## `POST /api/match-runs`

Summary: Create and start a match run from a validated import batch.

Auth: Required. Caller: `integration` or `operator`.

### Request Body

```json
{
  "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "top_k_per_project": 20,
  "scoring_config": {
    "semantic_weight": 0.35,
    "rerank_weight": 0.35,
    "skill_overlap_weight": 0.2,
    "resume_evidence_weight": 0.05,
    "preference_weight": 0.05
  }
}
```

### Response - `202 Accepted`

```json
{
  "id": "7d444840-9dc0-11d1-b245-5ffdce74fad2",
  "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "scoring_config_version": "mvp-v1",
  "created_at": "2026-06-26T12:10:00Z"
}
```

### Error Responses

| Status | Condition                                                 |
| ------ | --------------------------------------------------------- |
| `400`  | Import batch has blocking validation errors.              |
| `404`  | Import batch not found.                                   |
| `409`  | A match run with the same idempotency key already exists. |

### Side Effects

- Creates a `match_runs` record.
- Starts the match workflow.
- Emits `match_run.started` when execution begins.

---

## `GET /api/match-runs/{match_run_id}`

Summary: Fetch match-run status and metadata.

Auth: Required. Caller: `integration`, `operator`, or `reviewer`.

### Response - `200 OK`

```json
{
  "id": "7d444840-9dc0-11d1-b245-5ffdce74fad2",
  "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "scoring_config_version": "mvp-v1",
  "embedding_model_version": "BAAI/bge-m3",
  "reranker_model_version": "bge-reranker-v2",
  "generation_model_version": "groq:llama-3.1-8b-instant",
  "started_at": "2026-06-26T12:10:10Z",
  "completed_at": "2026-06-26T12:12:30Z",
  "failure_reason": null,
  "counts": {
    "projects": 8,
    "results": 160
  }
}
```

---

## `GET /api/match-runs/{match_run_id}/results`

Summary: Return persisted ranked results as JSON.

Auth: Required. Caller: `integration`, `operator`, or `reviewer`.

### Query Parameters

| Parameter           | Type | Required | Default | Description                          |
| ------------------- | ---- | -------- | ------- | ------------------------------------ |
| `project_id`        | UUID | No       | null    | Filter to one project.               |
| `limit_per_project` | int  | No       | `20`    | Max candidates returned per project. |

### Response - `200 OK`

```json
{
  "match_run_id": "7d444840-9dc0-11d1-b245-5ffdce74fad2",
  "projects": [
    {
      "project_id": "11111111-1111-1111-1111-111111111111",
      "project_title": "Multimodel AI Agents",
      "ranked_candidates": [
        {
          "rank": 1,
          "candidate_id": "22222222-2222-2222-2222-222222222222",
          "external_candidate_id": "MDS202504",
          "candidate_name": "Agnivesh Chatterjee",
          "final_score": 0.87,
          "scores": {
            "semantic": 0.89,
            "rerank": 0.91,
            "skill_overlap": 0.75,
            "resume_evidence": 0.7,
            "preference": 0.0
          },
          "explanation": "This candidate aligns strongly with the project's Python and computer vision requirements based on resume and imported profile evidence. The recommendation is strengthened by high semantic and reranker scores, while the remaining gap is Docker-specific project experience.",
          "warnings": []
        }
      ]
    }
  ]
}
```

---

## `GET /api/match-runs/{match_run_id}/export.xlsx`

Summary: Download an XLSX export generated from persisted match results.

Auth: Required. Caller: `integration`, `operator`, or `reviewer`.

### Response - `200 OK`

Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

The workbook must include:

- Match-run metadata.
- Project-centric ranked candidate sheets or sections.
- Component score columns.
- Explanation column.
- Data quality warning column.

### Error Responses

| Status | Condition                    |
| ------ | ---------------------------- |
| `404`  | Match run not found.         |
| `409`  | Match run has not completed. |

---

## Common Error Shape

```json
{
  "detail": "Human-readable error message"
}
```

Validation errors use FastAPI/Pydantic's standard `422` shape.

---

## Idempotency

Integration callers should send an `Idempotency-Key` header for:

- `POST /api/import-batches`
- `POST /api/import-batches/{batch_id}/files`
- `POST /api/match-runs`

Exact persistence behavior should be finalized before implementation.

---

## Open API Questions

| Question                                                                            | Required Before         | Status   |
| ----------------------------------------------------------------------------------- | ----------------------- | -------- |
| Service API key vs service JWT?                                                     | Phase 2 implementation  | Pending  |
| Should parsing be synchronous for small files or always backgrounded?               | Phase 2 implementation  | Pending  |
| Should result export be generated on demand or cached as an `import_file`/artifact? | Phase 10 implementation | Pending  |
| Should reviewer result edits be accepted in MVP?                                    | Post-MVP feedback phase | Deferred |

---

_API spec version 0.1 - review draft._
