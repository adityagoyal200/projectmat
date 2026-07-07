# Phase 4 - Symmetrical Matching & Recommendation APIs - Implementation Plan

## 1. Vector Embeddings & pgvector Retrieval

- **Module**: `backend/app/features/matching/embeddings.py`
- **Details**:
  - Implements the default embedding generation via `BAAI/bge-m3`.
  - Serializes candidate profiles and project descriptions.
  - Queries database using SQLAlchemy async commands with pgvector cosine distance metrics.

## 2. LLM Communication & Explanation Generation

- **Module**: `backend/app/features/matching/llm_client.py` and `match_explanation.py`
- **Details**:
  - `llm_client.py` provides configuration-driven calls to Groq or Ollama.
  - `match_explanation.py` builds the prompt context grounding the LLM in candidate facts, project prerequisites, and scoring results.
  - Implements deterministic backup templates to compile justifications if the model returns errors or is disabled.

## 3. Hybrid Scoring Engine

- **Module**: `backend/app/features/matching/scoring.py` and `skill_aliases.py`
- **Details**:
  - `scoring.py` computes:
    - Prerequisite overlap (exact matches and alias families via `skill_aliases.py`).
    - Experience depth (resume keywords, section headers, project counts).
    - Preference signals.
    - Final composite scores using configuration-driven weights.

## 4. Matching Service Orchestration

- **Module**: `backend/app/features/matching/service.py`
- **Details**:
  - Orchestrates candidate-project pairs recommendation.
  - Implements retrieve-and-rerank workflows (Stage-1 pgvector search followed by Stage-2 scoring and top-K LLM review).
  - Manages on-the-fly parsing and matching for uploaded resume PDFs.
