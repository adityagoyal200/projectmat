# Feature Specification Template

> Usage: Copy this file to `specs/features/<YYYY-MM-DD-feature-name>/requirements.md` and complete all sections before writing production code. An incomplete spec is a blocker.

---

## Feature Name

<!-- One-line title. -->

## Status

`[ ] Draft` | `[ ] Review` | `[ ] Approved` | `[ ] In Progress` | `[ ] Done` | `[ ] Deferred`

## Author

<!-- Author or team name. -->

## Date

<!-- YYYY-MM-DD -->

## Related Phase

<!-- e.g. Phase 2 - Bulk Workbook Import -->

## Related ADRs

<!-- Link ADRs if this feature depends on or changes architecture. -->

---

## 1. Problem Statement

<!--
What problem exists?
Who experiences it?
Why is it important?
What is the impact of not solving it?
Keep this to 3-5 sentences.
-->

---

## 2. Proposed Solution

<!--
At a high level, what will this feature do?
Avoid implementation details here. Focus on behavior visible to users, operators, or API consumers.
-->

---

## 3. User Stories

<!-- Format: As a <role>, I want to <action>, so that <outcome>. -->

- As a **[role]**, I want to **[action]**, so that **[outcome]**.
- As a **[role]**, I want to **[action]**, so that **[outcome]**.

---

## 4. Input and Output Contracts

<!--
For subsystem features, describe inbound data and outbound results.
For UI-only features, describe screen/state contracts instead.
-->

### Inputs

| Input | Required | Contract |
| ----- | -------- | -------- |
|       |          |          |

### Outputs

| Output | Consumer | Contract |
| ------ | -------- | -------- |
|        |          |          |

---

## 5. Scope

### In Scope

-
-

### Out of Scope

<!-- List related work that is explicitly deferred. -->

-
- ***

## 6. Solution Options and Trade-offs

### Option 1: MVP Approach

Description:

| Dimension            | Assessment |
| -------------------- | ---------- |
| Complexity           |            |
| Development effort   |            |
| Maintainability      |            |
| Scalability          |            |
| Performance          |            |
| Cost                 |            |
| Future extensibility |            |

### Option 2: Recommended Production Approach

Description:

| Dimension            | Assessment |
| -------------------- | ---------- |
| Complexity           |            |
| Development effort   |            |
| Maintainability      |            |
| Scalability          |            |
| Performance          |            |
| Cost                 |            |
| Future extensibility |            |

### Option 3: Enterprise Approach

Description:

| Dimension            | Assessment |
| -------------------- | ---------- |
| Complexity           |            |
| Development effort   |            |
| Maintainability      |            |
| Scalability          |            |
| Performance          |            |
| Cost                 |            |
| Future extensibility |            |

### Recommendation

<!-- Recommend exactly one approach and explain why the others are rejected. -->

---

## 7. Industry Practice

<!-- Briefly compare how startups, mid-sized SaaS companies, and large technology companies solve this problem. -->

---

## 8. API Design

<!--
List all new or modified endpoints.
For full endpoint details, create a corresponding API spec.
-->

| Method | Path       | Description | Auth Required | Caller/Role   |
| ------ | ---------- | ----------- | ------------- | ------------- |
| `GET`  | `/api/...` |             | Yes           | `operator`    |
| `POST` | `/api/...` |             | Yes           | `integration` |

---

## 9. Data Model Changes

<!--
List new tables, modified tables, indexes, and migrations.
No business-critical structured data should live only in JSON.
-->

### New Tables

```text
table_name
  column_name: type (constraints)
  column_name: type (constraints)
  indexes: [...]
```

### Modified Tables

| Table            | Change           | Reason |
| ---------------- | ---------------- | ------ |
| `existing_table` | Add column `foo` |        |

### Migrations

- [ ] Alembic migration file created.
- [ ] `alembic upgrade head` verified on a fresh database.
- [ ] `alembic downgrade base` verified.

---

## 10. Service Design

```python
class FeatureService:
    async def method_name(self, ...) -> ReturnType:
        """What this method does."""
        ...
```

---

## 11. AI / Generation Components

| Component | Module | Prompt Template | Fallback |
| --------- | ------ | --------------- | -------- |
|           |        |                 |          |

Rules:

- No direct LLM calls outside `ai/generation/`.
- AI provider failures must have tested fallback behavior.
- Generated text must be grounded in structured context.

---

## 12. Frontend Components

<!-- If no frontend is required, say so explicitly. -->

### New Pages

| Route  | File            | Description |
| ------ | --------------- | ----------- |
| `/...` | `src/pages/...` |             |

### New Components

| Component       | File                          | Props |
| --------------- | ----------------------------- | ----- |
| `ComponentName` | `src/components/features/...` |       |

### New Hooks

| Hook         | File                       | Purpose |
| ------------ | -------------------------- | ------- |
| `useFeature` | `src/hooks/use-feature.ts` |         |

---

## 13. Validation and Test Plan

<!-- Link `validation.md` or fill a compact summary here. -->

| Test Type   | What Is Tested                        | Expected Outcome                    |
| ----------- | ------------------------------------- | ----------------------------------- |
| Unit        | `service.method()` with valid input   | Returns correct result.             |
| Unit        | `service.method()` with invalid input | Raises expected error.              |
| Integration | `POST /api/...`                       | Returns expected status and schema. |

---

## 14. Definition of Done

- [ ] Architecture approved.
- [ ] All listed endpoints return correct status codes and response schemas.
- [ ] All listed service methods have unit tests.
- [ ] All listed endpoints have integration tests.
- [ ] AI fallback behavior is tested where relevant.
- [ ] Alembic migration applies and rolls back cleanly where relevant.
- [ ] FastAPI OpenAPI docs verified.
- [ ] README and `.env.example` updated if new setup or env vars were added.
- [ ] Ruff and ESLint pass with zero warnings where relevant.
- [ ] No `any` types in new TypeScript code.
- [ ] No raw SQL in service or router layers.
- [ ] No direct LLM calls outside `ai/generation/`.

---

## 15. Open Questions

| Question | Owner | Resolution Date | Decision |
| -------- | ----- | --------------- | -------- |
|          |       |                 |          |

---

_Feature Template version 2.0 - ProjectMatchAI_
