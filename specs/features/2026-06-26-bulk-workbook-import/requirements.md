# Phase 2 - Bulk Workbook Import

## Status

`[ ] Draft` | `[ ] Review` | `[ ] Approved` | `[ ] In Progress` | `[ ] Done` | `[ ] Deferred`

## Author

Antigravity

## Date

2026-06-26

## Related Phase

Phase 2 - Bulk Workbook Import

## 1. Problem Statement

Operators currently manage candidate and project lists across disconnected spreadsheets. Importing these spreadsheets into ProjectMatchAI requires validation and parsing so the system can work with typed staging records and report validation issues directly to operators.

## 2. Proposed Solution

Build an isolated workbook parser (`features/imports/`) that accepts an XLSX workbook, parses specific sheets (Students Info, Mentors info, Mentors-projects, Probable projects), and produces an `import_batch` along with row-level staged records and validation issues.

## 3. User Stories

- As a **Program Operator**, I want to **upload a candidate and project workbook**, so that **its data is imported into the system**.
- As a **Program Operator**, I want to **see validation issues for missing or malformed data synchronously**, so that **I can fix them in my spreadsheet or ignore them if they are non-critical**.

## 4. Input and Output Contracts

### Inputs

| Input     | Required | Contract                                         |
| --------- | -------- | ------------------------------------------------ |
| XLSX File | Yes      | Workbook containing expected sheets and columns. |

### Outputs

| Output                           | Consumer          | Contract                                                                                                                |
| -------------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Import Batch & Validation Issues | Frontend/Operator | Synchronous API response containing import batch ID, staged record summaries, and specific row/column validation flags. |

## 5. Scope

### In Scope

- XLSX upload and parsing endpoint.
- Header alias mapping for expected sheets.
- Row-level validation issue records generation.
- Returning validation issues synchronously in the API response.

### Out of Scope

- CSV import (deferred until XLSX stabilizes).
- Asynchronous batch processing with polling.

## 6. Solution Options and Trade-offs

### Recommendation

- **Validation Reporting**: As requested by the user, issues will be returned synchronously in the API response to provide immediate feedback. Missing values will be stored as nulls and flagged as validation issues.
- **Parsing Library**: The user suggested `pandas` for parsing. However, `specs/tech-stack.md` explicitly selects `openpyxl` and rejects `pandas` for production ingestion because it is less explicit for typed validation and source-row error reporting. We will proceed with `openpyxl` to adhere to the tech stack.

## 8. API Design

| Method | Path                    | Description                    | Auth Required | Caller/Role |
| ------ | ----------------------- | ------------------------------ | ------------- | ----------- |
| `POST` | `/api/imports/workbook` | Upload and parse XLSX workbook | No (MVP)      | `operator`  |

## 9. Data Model Changes

Uses tables from Phase 1 (`import_batches`, `import_files`, `import_validation_issues`). No new tables needed for Phase 2 MVP.

## 10. Service Design

```python
class WorkbookImportService:
    async def import_workbook(self, file_content: bytes) -> ImportBatchResult:
        """Parses the workbook, stages records, generates validation issues, and returns them synchronously."""
        ...
```
