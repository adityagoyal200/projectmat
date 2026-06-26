# Implementation Plan - Bulk Workbook Import

## 1. Domain Types and Schemas

1. Define Pydantic models for expected row schemas (Students, Mentors, Projects).
2. Define Pydantic models for API response (ImportBatchResult, ValidationIssue).

## 2. Parsing Logic (`openpyxl`)

1. Implement header alias mapping logic.
2. Implement sheet extraction (Students Info, Mentors info, Mentors-projects, Probable projects).
3. Implement row parsing to extract raw data, keeping track of sheet name and row number.

## 3. Validation and Staging Logic

1. Validate extracted rows against Pydantic models.
2. Generate validation issues for missing/malformed fields (using nulls for missing values and flagging them).
3. Create service method to orchestrate parsing, validation, and database storage for `import_batch` and `import_validation_issues`.

## 4. API Endpoints

1. Create `POST /api/imports/workbook` endpoint using FastAPI `UploadFile`.
2. Connect endpoint to the `WorkbookImportService`.
3. Return synchronous API response with validation results.

## 5. Tests

1. Write unit tests for `openpyxl` parsers using fixture workbooks.
2. Write integration tests for the API endpoint.
