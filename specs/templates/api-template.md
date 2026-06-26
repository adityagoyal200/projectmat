# API Endpoint Specification Template

> Usage: Copy this file to `specs/apis/<feature-name>-api.md` or to the relevant feature folder as `api.md`. One file per feature domain. This document is the authoritative API contract that backend implementation, frontend integration, and upstream systems must match.

---

## [Feature Name] API

**Base path**: `/api/[feature]`
**Authentication**: State the exact auth mode for this feature, for example `Public`, `Service API Key`, `Service JWT`, or `User JWT`.
**Content-Type**: `application/json` for request/response bodies unless noted.

---

## Auth and Roles

| Caller        | Auth Mode                          | Allowed Operations                                                        |
| ------------- | ---------------------------------- | ------------------------------------------------------------------------- |
| `integration` | Service API key or service JWT     | Submit imports and read machine-consumable results.                       |
| `operator`    | User JWT or internal admin auth    | Upload files, review validation issues, start match runs, export results. |
| `reviewer`    | User JWT or internal reviewer auth | Read match results and explanations.                                      |
| `public`      | None                               | Health or public metadata only.                                           |

Replace this table with the concrete roles for the feature being specified.

---

## Endpoints

### `[METHOD] [/api/path]`

**Summary**: One-line description of what this endpoint does.

**Auth**: Required or public. Role/caller: `integration` | `operator` | `reviewer` | `admin` | `public`

---

#### Request

**Path Parameters**

| Parameter | Type   | Required | Description          |
| --------- | ------ | -------- | -------------------- |
| `id`      | `UUID` | Yes      | Resource identifier. |

**Query Parameters**

| Parameter   | Type  | Required | Default | Description                                         |
| ----------- | ----- | -------- | ------- | --------------------------------------------------- |
| `page`      | `int` | No       | `1`     | Pagination page number.                             |
| `page_size` | `int` | No       | `20`    | Items per page, max 100 unless otherwise specified. |

**Request Body**

```json
{
  "field_name": "string",
  "another_field": 0,
  "optional_field": null
}
```

**Request Schema**

```python
class RequestSchema(BaseModel):
    field_name: str = Field(..., min_length=1, max_length=255, description="...")
    another_field: int = Field(..., ge=0, description="...")
    optional_field: str | None = Field(None, description="...")
```

---

#### Response

**Success - `200 OK`** or `201 Created` for creation endpoints.

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "field_name": "string",
  "created_at": "2026-06-26T12:00:00Z"
}
```

**Response Schema**

```python
class ResponseSchema(BaseModel):
    id: UUID
    field_name: str
    created_at: datetime
```

---

#### Error Responses

| Status Code                 | Condition                                                | Response Body                              |
| --------------------------- | -------------------------------------------------------- | ------------------------------------------ |
| `400 Bad Request`           | Request is syntactically valid but semantically invalid. | `{ "detail": "..." }`                      |
| `401 Unauthorized`          | Missing or invalid authentication.                       | `{ "detail": "Not authenticated" }`        |
| `403 Forbidden`             | Valid credentials but insufficient permissions.          | `{ "detail": "Insufficient permissions" }` |
| `404 Not Found`             | Resource does not exist or caller cannot access it.      | `{ "detail": "Resource not found" }`       |
| `409 Conflict`              | Idempotency or uniqueness conflict.                      | `{ "detail": "..." }`                      |
| `413 Payload Too Large`     | File or payload exceeds configured limit.                | `{ "detail": "Payload too large" }`        |
| `422 Unprocessable Entity`  | Pydantic validation failure.                             | `{ "detail": [...] }`                      |
| `429 Too Many Requests`     | Rate limit exceeded.                                     | `{ "detail": "Rate limit exceeded" }`      |
| `500 Internal Server Error` | Unexpected server error.                                 | `{ "detail": "Internal Server Error" }`    |

---

#### Side Effects

List side effects beyond returning data:

- Creates or updates database records.
- Writes an `audit_logs` record.
- Starts an import, parsing, matching, export, or generation job.
- Emits structured logs.
- Calls an AI provider through the centralized service layer.

---

#### Idempotency

State whether the endpoint is idempotent. For integration endpoints, specify any `Idempotency-Key` behavior.

---

#### Rate Limiting

| Scope      | Limit |
| ---------- | ----- |
| Per caller | TBD   |
| Per IP     | TBD   |

---

#### Example

**Request**

```bash
curl -X POST https://api.projectmatchai.com/api/... \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "example value"
  }'
```

**Response**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "field_name": "example value",
  "created_at": "2026-06-26T12:00:00Z"
}
```

---

## Pagination Contract

All list endpoints should follow this shape unless the API spec explicitly says otherwise:

```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

---

## Common Error Shape

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors:

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## FastAPI Router Registration

```python
# app/features/<feature>/router.py
router = APIRouter(prefix="/<feature>", tags=["<Feature>"])

# app/main.py
app.include_router(router, prefix="/api")
```

---

_API Template version 2.0 - ProjectMatchAI_
