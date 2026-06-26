# Validation and Test Plan: Bulk Intake and Matching

**Related Feature Spec**: `requirements.md`
**Related ADR**: `specs/adrs/ADR-0001-bulk-intake-matching-subsystem.md`
**Date**: 2026-06-26

---

## 1. Acceptance Criteria

- AC-1: A valid reference-shaped workbook creates an import batch with parsed candidate, mentor, and project rows.
- AC-2: Missing required sheets or headers produce structured validation errors.
- AC-3: Invalid but non-blocking data produces warnings and does not crash the import.
- AC-4: Candidate resume references are linked to uploaded/registered files when available.
- AC-5: Missing resume files are reported as warnings and candidates remain eligible for matching.
- AC-6: Canonical candidate, mentor, project, skill, and prerequisite records are created from parsed rows.
- AC-7: A match run records status, configuration versions, model versions, and timestamps.
- AC-8: Match results include rank, final score, component scores, and explanation.
- AC-9: LLM provider failure produces deterministic fallback explanations and no 500 response.
- AC-10: JSON and XLSX exports are generated from persisted results.

---

## 2. Test Fixtures

### Workbook Fixtures

| Fixture                         | Purpose                                                                  |
| ------------------------------- | ------------------------------------------------------------------------ |
| `reference_valid.xlsx`          | Minimal workbook matching the provided alumni mentorship workbook shape. |
| `missing_students_sheet.xlsx`   | Required sheet missing.                                                  |
| `missing_project_title.xlsx`    | Project row without title.                                               |
| `duplicate_registration.xlsx`   | Two candidate rows with the same registration number.                    |
| `invalid_emails.xlsx`           | Invalid candidate and mentor emails.                                     |
| `missing_resume_reference.xlsx` | Candidate references resume file not present in batch.                   |
| `empty_prerequisites.xlsx`      | Project rows without prerequisites.                                      |

### Resume Fixtures

| Fixture                | Purpose                            |
| ---------------------- | ---------------------------------- |
| `digital_resume.pdf`   | Digital PDF with extractable text. |
| `scanned_resume.pdf`   | OCR fallback path.                 |
| `invalid_resume.txt`   | File type rejection.               |
| `oversized_resume.pdf` | File size rejection.               |

---

## 3. Unit Tests

### Workbook Parsing

| Test                                        | Scenario                                     | Expected Outcome                    |
| ------------------------------------------- | -------------------------------------------- | ----------------------------------- |
| `test_detects_required_sheets`              | Workbook contains expected sheets.           | Parser maps sheets correctly.       |
| `test_missing_required_sheet_creates_error` | `Students Info` absent.                      | Error issue is produced.            |
| `test_header_aliases_normalize_columns`     | Headers contain line breaks or extra spaces. | Canonical field names are produced. |
| `test_empty_optional_sheet_allowed`         | `Probable projects` absent.                  | No blocking error.                  |

### Row Validation

| Test                                     | Scenario                                  | Expected Outcome                                    |
| ---------------------------------------- | ----------------------------------------- | --------------------------------------------------- |
| `test_candidate_requires_name`           | Candidate name missing.                   | Error issue code `candidate.name_missing`.          |
| `test_candidate_requires_external_id`    | Registration number missing.              | Error issue code `candidate.external_id_missing`.   |
| `test_duplicate_registration_detected`   | Duplicate registration number.            | Error issue code `candidate.external_id_duplicate`. |
| `test_na_email_treated_as_missing`       | Email is `N/A`.                           | No invalid email error; value stored as missing.    |
| `test_phone_preserved_as_text`           | Phone appears numeric in workbook.        | Canonical value is text.                            |
| `test_missing_resume_file_warns`         | `File` reference has no uploaded file.    | Warning issue code `candidate.resume_missing`.      |
| `test_project_requires_title`            | Project title missing.                    | Error issue code `project.title_missing`.           |
| `test_project_empty_abstract_warns`      | Abstract empty.                           | Warning issue code `project.abstract_missing`.      |
| `test_project_empty_prerequisites_warns` | Prerequisites empty.                      | Warning issue code `project.prerequisites_missing`. |
| `test_unlinked_mentor_warns`             | Project mentor not found in mentor sheet. | Warning issue code `mentor.unlinked`.               |

### Normalization

| Test                                        | Scenario                                | Expected Outcome                      |
| ------------------------------------------- | --------------------------------------- | ------------------------------------- |
| `test_candidate_normalization_idempotent`   | Normalize same batch twice.             | No duplicate candidate records.       |
| `test_mentor_normalization_links_email`     | Mentor appears in both sheets.          | One mentor with contact email.        |
| `test_project_normalization_links_mentor`   | Project row has known mentor.           | Project linked to mentor.             |
| `test_prerequisite_text_creates_skills`     | Prerequisites contain `Python, Docker`. | Skills/technologies are normalized.   |
| `test_selected_students_captured_as_signal` | Selected students column populated.     | Structured source signal is recorded. |

### Resume Parsing

| Test                                       | Scenario                               | Expected Outcome             |
| ------------------------------------------ | -------------------------------------- | ---------------------------- |
| `test_digital_pdf_parser_extracts_text`    | Digital PDF resume.                    | Non-empty parsed text.       |
| `test_ocr_fallback_when_pdf_text_empty`    | Digital parser returns low text count. | OCR parser invoked.          |
| `test_resume_parse_failure_records_status` | Parser raises controlled error.        | Document status is `failed`. |
| `test_resume_skills_keep_source_metadata`  | Resume parser finds skills.            | Skills source is `resume`.   |

### Scoring

| Test                                                 | Scenario                                    | Expected Outcome              |
| ---------------------------------------------------- | ------------------------------------------- | ----------------------------- |
| `test_hybrid_score_fixed_inputs`                     | Known component scores and weights.         | Exact expected final score.   |
| `test_missing_rerank_score_renormalizes_or_defaults` | Reranker unavailable.                       | Documented fallback behavior. |
| `test_skill_overlap_score`                           | Candidate has subset of prerequisites.      | Correct overlap fraction.     |
| `test_preference_signal_score`                       | Existing selected/preference signal exists. | Score component follows spec. |

### Explanation Generation

| Test                                | Scenario                              | Expected Outcome                       |
| ----------------------------------- | ------------------------------------- | -------------------------------------- |
| `test_explanation_prompt_grounded`  | Candidate and project facts provided. | Prompt includes only structured facts. |
| `test_llm_failure_uses_fallback`    | Provider raises exception.            | Non-empty fallback explanation.        |
| `test_explanation_method_persisted` | Fallback used.                        | `generation_method` is `fallback`.     |

---

## 4. Integration Tests

### Import Batch Lifecycle

| Test                                         | Scenario                             | Expected Outcome                                 |
| -------------------------------------------- | ------------------------------------ | ------------------------------------------------ |
| `test_create_import_batch`                   | Create empty batch.                  | Status `created`.                                |
| `test_attach_workbook_file`                  | Upload valid workbook.               | Import file record created.                      |
| `test_parse_valid_workbook`                  | Parse reference-shaped workbook.     | Candidate, mentor, and project staging succeeds. |
| `test_parse_invalid_workbook_reports_issues` | Parse missing sheet/header workbook. | Validation issues persisted.                     |
| `test_issue_listing_returns_row_context`     | Retrieve issues.                     | Sheet and row values present.                    |

### Resume Linking

| Test                                       | Scenario                                | Expected Outcome           |
| ------------------------------------------ | --------------------------------------- | -------------------------- |
| `test_link_resume_by_file_name`            | Candidate `File` matches upload.        | Candidate document linked. |
| `test_link_resume_by_registration_in_name` | File name contains registration number. | Candidate document linked. |
| `test_missing_resume_warning_not_failure`  | Resume absent.                          | Import batch can continue. |

### Match Run Lifecycle

| Test                                     | Scenario                              | Expected Outcome                          |
| ---------------------------------------- | ------------------------------------- | ----------------------------------------- |
| `test_create_match_run_from_ready_batch` | Batch normalized and embedded.        | Match run transitions to `completed`.     |
| `test_match_run_requires_ready_batch`    | Batch has blocking validation errors. | Match run rejected or failed with reason. |
| `test_match_results_persisted`           | Successful run.                       | Results exist for eligible projects.      |
| `test_match_run_failure_records_reason`  | Embedding service unavailable.        | Status `failed`, reason persisted.        |

### Results and Export

| Test                                 | Scenario                                 | Expected Outcome                                        |
| ------------------------------------ | ---------------------------------------- | ------------------------------------------------------- |
| `test_results_endpoint_shape`        | Fetch match results.                     | JSON includes project, candidates, scores, explanation. |
| `test_export_xlsx_contains_results`  | Download XLSX.                           | Workbook has ranked candidates and score columns.       |
| `test_export_uses_persisted_results` | Scores changed after run config changes. | Existing export remains tied to run results.            |

---

## 5. Security and Privacy Checks

| Check                     | Verification                        | Expected Outcome                                        |
| ------------------------- | ----------------------------------- | ------------------------------------------------------- |
| File type enforcement     | Upload unsupported file.            | Rejected with safe error.                               |
| File size enforcement     | Upload oversized resume.            | Rejected with safe error.                               |
| Path traversal protection | Upload filename with path segments. | Stored using sanitized name/path.                       |
| PII logging               | Inspect structured logs.            | No resume text or full phone/email dumped in logs.      |
| Error response safety     | Trigger unexpected parser error.    | Client sees safe message; logs have diagnostic context. |

---

## 6. Performance Checks

MVP targets are intentionally modest and should be revisited with real data.

| Metric              | Scenario                          | Target                                     |
| ------------------- | --------------------------------- | ------------------------------------------ |
| Workbook parse time | 100 candidates, 50 projects       | Less than 10 seconds locally.              |
| Candidate retrieval | 1,000 candidates, one project     | Less than 500 ms after embeddings/indexes. |
| Reranking           | Top 50 candidates for one project | Less than 3 seconds on development CPU.    |
| Export generation   | 50 projects, 20 candidates each   | Less than 10 seconds.                      |

---

## 7. Manual Validation Steps

1. Create an import batch.
2. Attach the reference-shaped workbook.
3. Attach a small set of matching resume PDFs.
4. Parse the workbook.
5. Review validation issue summary.
6. Normalize records.
7. Generate embeddings.
8. Start a match run.
9. Confirm status transitions to `completed`.
10. Fetch JSON results.
11. Download XLSX export.
12. Verify each project has ranked candidates, component scores, explanations, and warnings where applicable.

---

## 8. Definition of Done - Tests

- [ ] All parser unit tests pass.
- [ ] All validation rule tests pass.
- [ ] All normalization tests pass.
- [ ] All resume parsing/linking tests pass.
- [ ] All scoring tests pass with fixed expected values.
- [ ] All explanation fallback tests pass.
- [ ] Import lifecycle integration tests pass.
- [ ] Match-run lifecycle integration tests pass.
- [ ] Result/export integration tests pass.
- [ ] Security/privacy checks pass.
- [ ] No direct LLM calls outside `ai/generation/`.

---

## 9. Residual Risks

- Real workbooks may contain sheet/header variants not represented by the initial fixture set.
- Resume parsing quality may vary significantly across formats.
- Historical selected students may reflect manual constraints that the AI cannot infer.
- Matching quality cannot be fully validated until reviewer feedback or labeled outcomes exist.

---

_A feature is not complete until this validation plan passes or documented exceptions are approved._
