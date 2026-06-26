# Feature Specification Template

> **Usage**: Copy this file to `specs/features/<feature-name>.md` and complete all sections before writing any code. An incomplete spec is a blocker — do not start implementation until all required sections are filled.

---

## Feature Name

<!-- One-line title -->

## Status

`[ ] Draft` | `[ ] Review` | `[ ] Approved` | `[ ] In Progress` | `[ ] Done` | `[ ] Deferred`

## Author

<!-- Your name or team name -->

## Date

<!-- YYYY-MM-DD -->

## Related Phase

<!-- e.g. Phase 7 — Student Profile -->

---

## 1. Problem Statement

<!--
What problem does this feature solve?
Who experiences this problem?
What is the impact of not solving it?
Keep this to 3–5 sentences.
-->

## 2. Proposed Solution

<!--
At a high level, what will this feature do?
Avoid implementation details here — focus on behaviour visible to the user or API consumer.
-->

## 3. User Stories

<!--
Format: As a <role>, I want to <action>, so that <outcome>.
Include one story per distinct user interaction.
-->

- As a **[role]**, I want to **[action]**, so that **[outcome]**.
- As a **[role]**, I want to **[action]**, so that **[outcome]**.

## 4. Scope

### In Scope

-
-

### Out of Scope (Explicitly Deferred)

<!--
List things that might seem related but are NOT part of this feature.
This prevents scope creep during implementation.
-->

-
- ***

## 5. API Design

<!--
List all new or modified endpoints.
Use the format: METHOD /api/path — Brief description
For full endpoint spec, create a corresponding api-template.md.
-->

| Method | Path       | Description | Auth Required | Role    |
| ------ | ---------- | ----------- | ------------- | ------- |
| `GET`  | `/api/...` |             | ✅            | student |
| `POST` | `/api/...` |             | ✅            | mentor  |

---

## 6. Data Model Changes

<!--
List any new tables, columns, or indexes required.
If adding a new table, include the key columns.
No JSON for structured data — use proper columns and foreign keys.
-->

### New Tables

```
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

- [ ] Alembic migration file created: `alembic/versions/XXXX_<description>.py`
- [ ] `alembic upgrade head` verified on a fresh database
- [ ] `alembic downgrade base` verified

---

## 7. Service Design

<!--
Briefly describe the service layer. What classes and methods are introduced?
-->

```python
class FeatureService:
    async def method_name(self, ...) -> ReturnType:
        """What this method does."""
        ...
```

---

## 8. AI / Generation Components

<!--
If this feature uses the LLM or embedding pipeline, describe:
- Which generation module is used (ai/generation/explanation.py, roadmap.py, etc.)
- What prompt template is used (prompts/<name>.txt)
- What the fallback behaviour is if the AI call fails
-->

| Component | Module | Prompt Template | Fallback |
| --------- | ------ | --------------- | -------- |
|           |        |                 |          |

---

## 9. Frontend Components

<!--
List new pages, components, and hooks required.
-->

### New Pages

| Route          | File                    | Description |
| -------------- | ----------------------- | ----------- |
| `/student/...` | `src/pages/student/...` |             |

### New Components

| Component       | File                          | Props |
| --------------- | ----------------------------- | ----- |
| `ComponentName` | `src/components/features/...` |       |

### New Hooks

| Hook         | File                       | Purpose |
| ------------ | -------------------------- | ------- |
| `useFeature` | `src/hooks/use-feature.ts` |         |

---

## 10. Validation & Test Plan

<!--
What tests will be written? Use the validation-template.md for the full checklist.
-->

| Test Type   | What Is Tested                        | Expected Outcome                |
| ----------- | ------------------------------------- | ------------------------------- |
| Unit        | `service.method()` with valid input   | Returns correct result          |
| Unit        | `service.method()` with invalid input | Raises `ValueError`             |
| Integration | `POST /api/...`                       | Returns 200 with correct schema |
| Integration | `POST /api/...` without auth          | Returns 401                     |

---

## 11. Definition of Done

<!--
This section is the contract. The feature is not done until every item is checked.
-->

- [ ] All listed endpoints return correct status codes and response schemas
- [ ] All listed service methods have unit tests
- [ ] All listed endpoints have integration tests
- [ ] TypeScript strict mode passes (`tsc --noEmit`)
- [ ] Ruff and ESLint pass with zero warnings
- [ ] Alembic migration applies and rolls back cleanly
- [ ] API documentation updated (FastAPI auto-docs verified)
- [ ] `README.md` updated if new environment variables were added to `.env.example`
- [ ] No `any` types in new TypeScript code
- [ ] No raw SQL in service layer

---

## 12. Open Questions

<!--
List any unresolved design decisions. Assign an owner and a resolution date.
-->

| Question | Owner | Resolution Date | Decision |
| -------- | ----- | --------------- | -------- |
|          |       |                 |          |

---

_Template version 1.0 — ProjectMatchAI_
