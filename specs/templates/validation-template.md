# Validation and Test Plan Template

> Usage: Copy this file to `specs/features/<YYYY-MM-DD-feature-name>/validation.md`. Complete it alongside the feature spec before implementation begins. Testing is part of the feature contract.

---

## Validation Plan - [Feature Name]

**Phase**: [e.g. Phase 2 - Bulk Workbook Import]
**Related Feature Spec**: [`requirements.md`](requirements.md)
**Author**:
**Date**:

---

## 1. Acceptance Criteria

- AC-1:
- AC-2:
- AC-3:

---

## 2. Test Fixtures

| Fixture | File | Purpose |
| ------- | ---- | ------- |
|         |      |         |

---

## 3. Unit Tests

Unit tests cover pure logic. No database, HTTP, external service, or live AI provider should be required.

| Test           | Component               | Scenario     | Expected Outcome         |
| -------------- | ----------------------- | ------------ | ------------------------ |
| `test_example` | `ServiceClass.method()` | Valid input. | Returns expected result. |

Coverage target:

- Public service methods.
- Validators and normalizers.
- Parsers.
- Scoring functions.
- AI prompt construction and fallback behavior where relevant.

---

## 4. Integration Tests

Integration tests verify endpoint and persistence behavior with a real test database.

| Test                   | Endpoint or Flow | Scenario           | Auth       | Expected Status | Expected Outcome  |
| ---------------------- | ---------------- | ------------------ | ---------- | --------------- | ----------------- |
| `test_create_resource` | `POST /api/...`  | Valid payload.     | Required   | `201`           | Resource created. |
| `test_missing_auth`    | `POST /api/...`  | No credentials.    | Missing    | `401`           | Request rejected. |
| `test_forbidden_role`  | `POST /api/...`  | Wrong caller role. | Wrong role | `403`           | Request rejected. |

---

## 5. AI / Generation Tests

If this feature uses AI services, list the exact tests here.

| Test                             | Component          | Scenario                   | Expected Outcome                       |
| -------------------------------- | ------------------ | -------------------------- | -------------------------------------- |
| `test_prompt_grounded`           | Generation service | Structured facts provided. | Prompt includes only approved context. |
| `test_provider_failure_fallback` | Generation service | Provider raises exception. | Deterministic fallback returned.       |

---

## 6. Frontend Tests

If no frontend is required, state that explicitly.

| Test | Component or Hook | Scenario | Expected Outcome |
| ---- | ----------------- | -------- | ---------------- |
|      |                   |          |                  |

---

## 7. Security and Privacy Tests

| Check                   | Verification                                 | Expected Outcome                                   |
| ----------------------- | -------------------------------------------- | -------------------------------------------------- |
| Authentication required | Call protected endpoint without credentials. | `401`, not `200` or `500`.                         |
| Authorization enforced  | Call endpoint with wrong role/caller.        | `403` or safe `404`, as specified.                 |
| Payload limits enforced | Submit oversized body or file.               | `413` before expensive processing.                 |
| PII-safe logs           | Inspect structured logs.                     | Sensitive raw data is not emitted.                 |
| Error detail safety     | Trigger unexpected error.                    | Client sees safe message; logs retain diagnostics. |

---

## 8. Edge Cases and Boundary Conditions

| Edge Case              | Expected Behavior                                  |
| ---------------------- | -------------------------------------------------- |
| Empty string input     | Validation error, not silent success.              |
| Duplicate request      | Idempotency or conflict behavior follows API spec. |
| AI service unavailable | Graceful degradation or documented failure state.  |
| Database timeout       | Controlled error and structured log.               |

---

## 9. Performance Checks

| Metric | Scenario | Target |
| ------ | -------- | ------ |
|        |          |        |

---

## 10. Manual Verification Steps

1. Start the required local services.
2. Run the documented setup command.
3. Execute the feature workflow.
4. Verify outputs match the feature spec.
5. Confirm no unsafe errors or logs appear.

---

## 11. Definition of Done - Tests

Backend:

- [ ] All listed unit tests are written and passing.
- [ ] All listed integration tests are written and passing.
- [ ] All listed security/privacy checks pass.
- [ ] `pytest` runs with zero failures.
- [ ] New code coverage is appropriate for risk and complexity.
- [ ] No test uses `time.sleep()` where deterministic timing or async utilities can be used.
- [ ] No test is skipped without a documented reason.

Frontend:

- [ ] All listed component and hook tests pass, if relevant.
- [ ] `npm run test` runs with zero failures, if relevant.
- [ ] `tsc --noEmit` passes, if relevant.

Type safety and quality:

- [ ] Python type checks pass on modified files where configured.
- [ ] TypeScript type checks pass on modified files where configured.
- [ ] Ruff passes with zero warnings.
- [ ] ESLint passes with zero warnings, if relevant.
- [ ] No raw SQL in service or router layers.

---

## 12. Residual Risks

| Risk | Mitigation or Owner |
| ---- | ------------------- |
|      |                     |

---

_Validation Template version 2.0 - ProjectMatchAI_
