# Validation & Test Plan Template

> **Usage**: Copy this file to `specs/validation/<feature-name>-validation.md`. Complete it alongside the `feature-template.md` before implementation begins. The test plan is part of the feature spec — not an afterthought.

---

## Validation Plan — [Feature Name]

**Phase**: [e.g. Phase 7 — Student Profile]
**Related Feature Spec**: [`specs/features/<feature-name>.md`](../features/<feature-name>.md)
**Author**:
**Date**:

---

## Test Inventory

### Unit Tests

Unit tests cover pure logic — no database, no HTTP, no external services. All dependencies are mocked or injected with test doubles.

| #   | Test File                     | Function / Class Under Test | Scenario               | Expected Outcome                 |
| --- | ----------------------------- | --------------------------- | ---------------------- | -------------------------------- |
| U1  | `tests/unit/test_<module>.py` | `ServiceClass.method()`     | Valid input            | Returns correct result           |
| U2  | `tests/unit/test_<module>.py` | `ServiceClass.method()`     | Invalid input          | Raises `ValueError` with message |
| U3  | `tests/unit/test_<module>.py` | `utility_function()`        | Edge case: empty input | Returns empty list, not error    |

**Coverage target**: All public functions and methods in `service.py`, utility modules, and `ai/` modules for this feature.

---

### Integration Tests

Integration tests verify endpoint behaviour with a real test database. Use `httpx.AsyncClient` with `pytest-asyncio`. No mocking of the database layer.

| #   | Test File                             | Endpoint          | Scenario               | Auth            | Expected Status | Expected Response                          |
| --- | ------------------------------------- | ----------------- | ---------------------- | --------------- | --------------- | ------------------------------------------ |
| I1  | `tests/integration/test_<feature>.py` | `POST /api/...`   | Valid payload          | ✅              | `201`           | `{ "id": ..., "field": ... }`              |
| I2  | `tests/integration/test_<feature>.py` | `POST /api/...`   | Missing required field | ✅              | `422`           | Validation error detail                    |
| I3  | `tests/integration/test_<feature>.py` | `POST /api/...`   | No auth token          | ❌              | `401`           | `{ "detail": "Not authenticated" }`        |
| I4  | `tests/integration/test_<feature>.py` | `POST /api/...`   | Wrong role             | ✅ (wrong role) | `403`           | `{ "detail": "Insufficient permissions" }` |
| I5  | `tests/integration/test_<feature>.py` | `GET /api/.../id` | Non-existent resource  | ✅              | `404`           | `{ "detail": "Resource not found" }`       |

---

### AI / Generation Tests

If this feature uses `ai/generation/` or the matching pipeline, list specific tests here.

| #   | Test File                                | Component                      | Scenario                             | Expected Outcome                                        |
| --- | ---------------------------------------- | ------------------------------ | ------------------------------------ | ------------------------------------------------------- |
| A1  | `tests/unit/test_generation_<module>.py` | `GenerationService.generate()` | Valid input, LLM returns text        | Returns non-empty string                                |
| A2  | `tests/unit/test_generation_<module>.py` | `GenerationService.generate()` | LLM raises exception                 | Returns fallback template string, no exception raised   |
| A3  | `tests/unit/test_generation_<module>.py` | Prompt construction            | Specific student/project combination | Prompt contains student skills and project requirements |

---

### Frontend Tests

| #   | Test File                                            | Component / Hook | Scenario                 | Expected Outcome               |
| --- | ---------------------------------------------------- | ---------------- | ------------------------ | ------------------------------ |
| F1  | `src/components/features/.../ComponentName.test.tsx` | `ComponentName`  | Renders with valid props | Correct content visible in DOM |
| F2  | `src/components/features/.../ComponentName.test.tsx` | `ComponentName`  | Loading state            | Skeleton/spinner visible       |
| F3  | `src/hooks/use-feature.test.ts`                      | `useFeature()`   | API returns error        | Error state exposed correctly  |

---

### Security Tests

| #   | Scenario                                    | How to Verify                                      |
| --- | ------------------------------------------- | -------------------------------------------------- |
| S1  | Unauthenticated request                     | Returns `401`, not `200` or `500`                  |
| S2  | Student cannot access mentor-only endpoint  | Returns `403`                                      |
| S3  | User cannot access another user's resources | Returns `404` (not `403` — don't reveal existence) |
| S4  | Rate limiting on login/sensitive endpoints  | After N requests, returns `429`                    |
| S5  | Oversized payload (e.g., 100MB file upload) | Returns `413` before processing begins             |

---

### Edge Cases & Boundary Conditions

<!--
List non-obvious edge cases specific to this feature.
These are the cases most likely to be missed during initial implementation.
-->

| #   | Edge Case                                                      | Expected Behaviour                                             |
| --- | -------------------------------------------------------------- | -------------------------------------------------------------- |
| E1  | Empty string input                                             | Validation error, not silent success                           |
| E2  | Maximum length input                                           | Accepted without truncation                                    |
| E3  | Concurrent requests (e.g., two profile updates simultaneously) | Last-write-wins or conflict error (document which)             |
| E4  | AI service unavailable                                         | Graceful degradation — feature still works without AI response |
| E5  | Database connection timeout                                    | `503` with retry-after header                                  |

---

## Definition of Done — Tests

Check every item before marking the feature as complete:

**Backend**

- [ ] All unit tests listed above are written and passing
- [ ] All integration tests listed above are written and passing
- [ ] All security tests pass
- [ ] `pytest` runs with zero failures: `pytest tests/ -v`
- [ ] `pytest --cov=app --cov=ai --cov-report=term-missing` shows ≥ 80% coverage on new code
- [ ] No test uses `time.sleep()` — use `asyncio.sleep()` or mock timers
- [ ] No test is marked `@pytest.mark.skip` without a documented reason

**Frontend**

- [ ] All listed component and hook tests pass
- [ ] `npm run test` runs with zero failures
- [ ] `tsc --noEmit` passes with strict mode

**Type Safety**

- [ ] `pyright` passes on all modified Python files
- [ ] `tsc --noEmit` passes on all modified TypeScript files
- [ ] No `# type: ignore` comments added without documented justification

**Code Quality**

- [ ] `ruff check .` passes with zero warnings
- [ ] `ruff format .` produces no diff
- [ ] `eslint .` passes with zero warnings
- [ ] No `any` type in new TypeScript code
- [ ] No raw SQL in `service.py` or `router.py`

---

## Test Data Requirements

<!--
List any fixtures, seed data, or test database setup required for this feature's tests.
-->

| Fixture             | File                                     | Description                             |
| ------------------- | ---------------------------------------- | --------------------------------------- |
| `student_user`      | `tests/conftest.py`                      | A confirmed student with verified email |
| `mentor_user`       | `tests/conftest.py`                      | A mentor with one open project          |
| `confirmed_profile` | `tests/fixtures/profiles.py`             | A student profile with 3 skills         |
| `sample_pdf`        | `tests/fixtures/files/sample_resume.pdf` | A real digital PDF for parsing tests    |

---

## Manual Verification Steps

<!--
Tests that cannot be easily automated — verify manually before marking Done.
-->

1. Start the dev environment: `docker compose up`
2. Navigate to `http://localhost:3000` in a browser
3. [Specific manual steps to verify the feature works as intended]
4. Confirm no JavaScript console errors appear
5. Confirm network requests in DevTools return expected status codes

---

_Validation Template version 1.0 — ProjectMatchAI_
