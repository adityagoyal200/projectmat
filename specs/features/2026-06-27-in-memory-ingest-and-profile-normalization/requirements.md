# Phase 3 - In-Memory Ingest & Profile Normalization - Requirements

## Status

`[x] Done`

## Author

Antigravity

## Date

2026-06-27

## Related Phase

Phase 3 - In-Memory Ingest & Profile Normalization

## 1. Problem Statement

To enable hybrid matching, ProjectMatchAI needs access to candidate resumes, developer handles, and project information. However, storing raw PDF resumes on disk raises privacy concerns. The system must fetch these files from Google Drive folder links, extract their text in-memory, parse the content for developer profiles and achievements, persist candidates/projects canonical records, and expose discoverability APIs.

## 2. Proposed Solution

1. **Google Drive Extractor**: Add helper utilities to parse folder sharing URLs and download resume PDFs into memory.
2. **In-Memory PDF Reader**: Integrate `PyMuPDF` (`fitz`) to extract text contents without writing files to local disk.
3. **Profile Handle Regex Parser**: Scan extracted text for GitHub, LeetCode, Codeforces, Kaggle, Scholar profile patterns, achievements, and live URLs.
4. **Discoverability Endpoints**: Expose simple REST endpoints to query candidates and project details.

## 3. User Stories

- As an **Operator**, I want to **provide a Google Drive resume folder link**, so that **resumes are automatically matched to students and parsed**.
- As an **Operator**, I want **resumes to be processed purely in-memory**, so that **no raw candidate PDFs remain on the server disk**.
- As a **Reviewer**, I want to **query candidates and project records via API**, so that **I can inspect the canonical staging data**.

## 4. Input and Output Contracts

### Inputs

- **Google Drive Folder URL**: A shared folder link containing candidate resume PDF files.
- **Workbook resume filename**: Links candidate rows to their respective PDF file in the Drive folder by matching registration numbers.

### Outputs

- **Canonical database records**: Populated tables for candidates, documents, and skills.
- **Discoverability JSON response**: List and detail queries for candidates and projects.

## 5. Scope

### In Scope

- Hyperlink extraction from cell values in workbook imports.
- Google Drive resume downloader (in-process).
- In-memory PDF parsing via PyMuPDF.
- Staging of candidate profiles, contact details, and achievements.
- API endpoints for candidate and project listings.

### Out of Scope

- Local storage of raw resume PDFs.
- Optical Character Recognition (OCR) for scanned PDFs (handled under Phase 6 if needed).

## 6. API Design

| Method | Path                   | Description                      | Roles      |
| ------ | ---------------------- | -------------------------------- | ---------- |
| `GET`  | `/api/candidates`      | List and filter staged students. | `operator` |
| `GET`  | `/api/candidates/{id}` | Get specific candidate details.  | `operator` |
| `GET`  | `/api/projects`        | List and filter projects.        | `operator` |
| `GET`  | `/api/projects/{id}`   | Get project details.             | `operator` |

## 7. Data Model Changes

Populates canonical tables: `candidates`, `candidate_contacts`, `candidate_documents`. Adds `resumes_url` field to `import_batches` to store the drive path.

## 8. Definition of Done

- [x] Resumes are successfully fetched and parsed in-memory.
- [x] Staged candidate records populate developer profile handles and achievements.
- [x] Candidates and projects endpoints list and return detailed entries.
- [x] Unit and integration tests cover PDF parsing and query routes.
