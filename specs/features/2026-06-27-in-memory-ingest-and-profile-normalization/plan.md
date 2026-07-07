# Phase 3 - In-Memory Ingest & Profile Normalization - Implementation Plan

## 1. Google Drive Integration & In-Memory Downloading

- **Module**: `backend/app/features/imports/drive_downloader.py`
- **Details**:
  - Implements Google Drive folder parsing using `gdown` or raw HTTP calls.
  - Downloads PDF files directly to raw byte streams.
  - Uses `fitz` (`PyMuPDF`) to read and extract text from bytes, ensuring no PDFs are written to local storage.

## 2. Profile Parsing Logic

- **Module**: `backend/app/features/imports/profile_parser.py`
- **Details**:
  - Regex-based username extraction from resume text for GitHub, LeetCode, Codeforces, Kaggle, and Scholar profiles.
  - Extraction of candidate portfolio achievements and live site link references.

## 3. Database Persistence & Background Workers

- **Module**: `backend/app/features/imports/service.py`
- **Details**:
  - Launches async background worker `ingest_resumes_background_task` after workbook validation succeeds.
  - Matches candidate records by registration numbers extracted from resume file names.
  - Parses PDFs in an executor thread, then saves profile handles and raw text to candidate tables.

## 4. API Endpoints

- **Candidate Discoverability**:
  - Router: `backend/app/features/candidates/router.py`
  - Handler: `GET /api/candidates` and `GET /api/candidates/{id}`
- **Project Discoverability**:
  - Router: `backend/app/features/projects/router.py`
  - Handler: `GET /api/projects` and `GET /api/projects/{id}`
