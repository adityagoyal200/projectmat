# Validation Plan - Bulk Workbook Import

## 1. Acceptance Criteria

- AC-1: Uploading a valid workbook produces an `import_batch` and staged records.
- AC-2: Missing required sheets or columns produce structured validation issues returned synchronously.
- AC-3: Null values are accepted and flagged appropriately based on sheet requirements.

## 2. Unit Tests

- `test_parser_valid_workbook`: Valid workbook parses into expected typed rows.
- `test_parser_missing_sheet`: Parser reports missing mandatory sheet.
- `test_parser_missing_columns`: Parser handles missing/malformed columns and flags issues.
- `test_service_creates_batch`: Service orchestrates batch and issue creation.

## 3. Integration Tests

- `test_upload_workbook_api`: `POST /api/imports/workbook` returns `200` with batch details and issues.
- `test_upload_invalid_file`: `POST /api/imports/workbook` rejects non-XLSX files with `400`.

## 4. Edge Cases

- Empty rows in workbook: Ignored or flagged.
- Extremely large workbook: Synchronous response might timeout; configure upload limits.

## 11. Definition of Done - Tests

- [ ] All listed unit tests are written and passing.
- [ ] All listed integration tests are written and passing.
- [ ] Type checks pass.
- [ ] Ruff passes with zero warnings.
