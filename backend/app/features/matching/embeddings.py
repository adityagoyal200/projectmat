"""Text embedding and cosine similarity for semantic fit.

Uses BGE-M3 or lightweight fallback.
"""

from __future__ import annotations

import asyncio
import math
import re
from collections import Counter

import structlog

from app.config import settings

logger = structlog.get_logger()

_model = None
_model_load_attempted = False


def _tokenize(text: str) -> Counter[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]{1,}", text.lower())
    return Counter(tokens)


def _cosine_counter(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b[t] for t in a if t in b)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _fallback_similarity(text_a: str, text_b: str) -> float:
    """Token-overlap cosine when the embedding model is unavailable."""
    return round(_cosine_counter(_tokenize(text_a), _tokenize(text_b)), 4)


def _load_model():
    global _model, _model_load_attempted
    if _model_load_attempted:
        return _model
    _model_load_attempted = True
    if not settings.EMBEDDINGS_ENABLED:
        return None
    try:
        from sentence_transformers import (
            SentenceTransformer,  # type: ignore[import-untyped]
        )

        logger.info("Loading embedding model", model=settings.BGE_MODEL_NAME)
        _model = SentenceTransformer(settings.BGE_MODEL_NAME)
        return _model
    except Exception as e:
        logger.warn(
            "Embedding model unavailable; using token-similarity fallback",
            error=str(e),
        )
        return None


def _encode_sync(text: str) -> list[float]:
    model = _load_model()
    if model is None:
        return []
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def _cosine_vectors(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return round(max(0.0, min(1.0, dot)), 4)


async def embedding_similarity(text_a: str, text_b: str) -> tuple[float, str]:
    """Return (similarity 0-1, method description)."""
    a = text_a.strip()
    b = text_b.strip()
    if not a or not b:
        return 0.0, "Empty profile text; embedding similarity is 0.0."

    loop = asyncio.get_running_loop()
    model = _load_model()
    if model is None:
        score = _fallback_similarity(a, b)
        return (
            score,
            f"Token-cosine fallback similarity = {score:.4f} "
            "(embedding model not loaded).",
        )

    vec_a, vec_b = await asyncio.gather(
        loop.run_in_executor(None, _encode_sync, a),
        loop.run_in_executor(None, _encode_sync, b),
    )
    if not vec_a or not vec_b:
        score = _fallback_similarity(a, b)
        return score, f"Token-cosine fallback similarity = {score:.4f}."

    score = _cosine_vectors(vec_a, vec_b)
    return (
        score,
        f"BGE embedding cosine similarity ({settings.BGE_MODEL_NAME}) = {score:.4f}.",
    )


def build_candidate_profile_text(
    candidate_name: str,
    candidate_skills: list[str],
    resume_text: str,
    *,
    max_resume_chars: int = 4000,
) -> str:
    skills_part = (
        ", ".join(candidate_skills) if candidate_skills else "no skills listed"
    )
    resume_part = resume_text[:max_resume_chars].strip() if resume_text else ""
    return f"Candidate: {candidate_name}. Skills: {skills_part}. Resume: {resume_part}"


def build_project_profile_text(
    project_title: str,
    project_abstract: str,
    prerequisites: list[str],
) -> str:
    prereq_part = ", ".join(prerequisites) if prerequisites else "none"
    abstract = project_abstract.strip() if project_abstract else "no abstract"
    return (
        f"Project: {project_title}. Abstract: {abstract}. Prerequisites: {prereq_part}."
    )
