# API Endpoint Specification Template

> **Usage**: Copy this file to `specs/apis/<feature-name>-api.md`. One file per feature domain (e.g., `auth-api.md`, `matching-api.md`). Fill in one section per endpoint. This document is the authoritative spec that the backend implementation and frontend integration must both match.

---

## [Feature Name] API

**Base path**: `/api/[feature]`
**Authentication**: All endpoints require `Authorization: Bearer <access_token>` unless marked `Public`.
**Content-Type**: `application/json` for all request/response bodies unless noted.

---

## Endpoints

---

### `[METHOD] [/api/path]`

**Summary**: One-line description of what this endpoint does.

**Auth**: ✅ Required — Role: `student` | `mentor` | `admin` | `public`

---

#### Request

**Path Parameters**

| Parameter | Type   | Required | Description         |
| --------- | ------ | -------- | ------------------- |
| `id`      | `UUID` | ✅       | Resource identifier |

**Query Parameters**

| Parameter   | Type  | Required | Default | Description              |
| ----------- | ----- | -------- | ------- | ------------------------ |
| `page`      | `int` | ❌       | `1`     | Pagination page number   |
| `page_size` | `int` | ❌       | `20`    | Items per page (max 100) |

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
    optional_field: Optional[str] = Field(None, description="...")
```

---

#### Response

**Success — `200 OK`** (or `201 Created` for POST)

```json
{
  "id": "uuid",
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

| Status Code                | Condition                         | Response Body                                                 |
| -------------------------- | --------------------------------- | ------------------------------------------------------------- |
| `400 Bad Request`          | Request body fails validation     | `{ "detail": [{"loc": [...], "msg": "...", "type": "..."}] }` |
| `401 Unauthorized`         | Missing or invalid access token   | `{ "detail": "Not authenticated" }`                           |
| `403 Forbidden`            | Valid token but insufficient role | `{ "detail": "Insufficient permissions" }`                    |
| `404 Not Found`            | Resource does not exist           | `{ "detail": "Resource not found" }`                          |
| `422 Unprocessable Entity` | Pydantic validation failure       | `{ "detail": [...] }`                                         |
| `429 Too Many Requests`    | Rate limit exceeded               | `{ "detail": "Rate limit exceeded" }`                         |

---

#### Side Effects

<!--
List any side effects this endpoint has beyond returning data.
Examples: sends an email, creates a notification, writes an audit log, triggers an async task.
-->

- Creates a `notifications` record of type `...` for user `...`
- Writes an `audit_logs` record with action `...`
- Triggers background task: `...`

---

#### Rate Limiting

| Scope    | Limit                |
| -------- | -------------------- |
| Per IP   | `10 requests/minute` |
| Per User | `60 requests/minute` |

---

#### Example

**Request**

```bash
curl -X POST https://api.projectmatchai.com/api/... \
  -H "Authorization: Bearer eyJ..." \
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

<!-- Repeat the above block for each endpoint in the feature -->

---

## Pagination Contract

All list endpoints follow a consistent pagination shape:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

---

## Common Error Shape

All error responses follow:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors (422):

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

_API Template version 1.0 — ProjectMatchAI_
