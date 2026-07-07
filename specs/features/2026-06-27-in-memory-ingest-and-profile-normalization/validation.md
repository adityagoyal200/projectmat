# Phase 3 - In-Memory Ingest & Profile Normalization - Validation Plan

## 1. Acceptance Criteria

- **AC-1**: Workbook Google Drive URL matches the folder sharing layout.
- **AC-2**: Files download and parse cleanly in-memory.
- **AC-3**: Candidate stage records match normalized records by registration code.
- **AC-4**: Candidates and Projects endpoints return correct database records.

## 2. Unit Tests

- `test_profile_parser`: Parses candidate developer usernames and links.
- `test_parse_pdf_bytes`: Checks `PyMuPDF` text extraction on raw test document bytes.

## 3. Integration Tests

- `test_discoverability_api`: Verifies `GET /api/candidates` and `GET /api/projects` list and filter items properly.

## 4. Edge Cases

- Mismatched filenames: Filenames with missing/malformed registration IDs produce warning logs.
- Corrupted PDFs: Parser handles unreadable file streams and sets status to `failed` rather than crashing the background worker.

## 5. Definition of Done

- [x] All listed unit tests are written and passing.
- [x] In-memory PDF extraction is confirmed via tests.
- [x] Type checks and formatting check out clean.
