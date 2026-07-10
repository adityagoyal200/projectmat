"""Text embedding and cosine similarity for semantic fit.

Uses BGE-M3 or lightweight fallback.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
import threading
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor

import structlog

from app.config import settings

logger = structlog.get_logger()

# All encodes go through this single-thread executor. Torch already saturates
# every core for one encode, so parallel encodes only thrash the CPU — and two
# concurrent batch computes (e.g. a user reloading mid-run) used to grind the
# whole backend to a halt. One thread serializes them and keeps the default
# executor free for other work (PDF rendering, file parsing).
_ENCODE_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="embeddings")

_model = None
_model_load_attempted = False
_model_load_lock = threading.Lock()


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
    """Load the sentence-transformer once, guarded by a lock.

    Loading BGE-M3 takes ~30s on CPU, so this must only ever run inside a
    worker thread (never on the event loop) — callers go through
    run_in_executor or the warm-up thread.
    """
    global _model, _model_load_attempted
    with _model_load_lock:
        if _model_load_attempted:
            return _model
        _model_load_attempted = True
        if not settings.EMBEDDINGS_ENABLED:
            return None
        try:
            from sentence_transformers import (
                SentenceTransformer,  # pyright: ignore[reportMissingImports]
            )

            logger.info("Loading embedding model", model=settings.BGE_MODEL_NAME)
            hf_token = settings.HF_TOKEN.strip() or None
            if hf_token:
                os.environ.setdefault("HF_TOKEN", hf_token)
                os.environ.setdefault("HUGGINGFACE_HUB_TOKEN", hf_token)
            _model = SentenceTransformer(settings.BGE_MODEL_NAME, token=hf_token)
            logger.info("Embedding model loaded", model=settings.BGE_MODEL_NAME)
            return _model
        except Exception as e:
            logger.warn(
                "Embedding model unavailable; using token-similarity fallback",
                error=str(e),
            )
            return None


def warm_up_embeddings() -> None:
    """Kick off the (slow) model load in a background daemon thread.

    Called at app startup so the first matching request doesn't pay the
    ~30s CPU load — and, because _load_model used to run on the event loop,
    doesn't freeze every other request while it loads. Non-blocking; safe to
    call more than once.
    """
    if not settings.EMBEDDINGS_ENABLED or _model_load_attempted:
        return
    threading.Thread(
        target=_load_model, name="embedding-model-warmup", daemon=True
    ).start()


# text → embedding vector, LRU-capped. A manual OrderedDict (instead of
# functools.lru_cache) so precompute_embeddings can batch-fill it.
_ENCODE_CACHE_MAX = 2048
_encode_cache: OrderedDict[str, list[float]] = OrderedDict()
_encode_cache_lock = threading.Lock()


def _cache_get(text: str) -> list[float] | None:
    with _encode_cache_lock:
        vec = _encode_cache.get(text)
        if vec is not None:
            _encode_cache.move_to_end(text)
        return vec


def _cache_put(text: str, vec: list[float]) -> None:
    with _encode_cache_lock:
        _encode_cache[text] = vec
        _encode_cache.move_to_end(text)
        while len(_encode_cache) > _ENCODE_CACHE_MAX:
            _encode_cache.popitem(last=False)


def _encode_sync(text: str) -> list[float]:
    cached = _cache_get(text)
    if cached is not None:
        return cached
    model = _load_model()
    if model is None:
        return []
    vec = model.encode(text, normalize_embeddings=True).tolist()
    _cache_put(text, vec)
    return vec


def _encode_many_sync(texts: list[str]) -> None:
    """Encode all uncached texts in one batched model call, filling the cache.

    Batching lets the model vectorize across texts — dramatically faster on
    CPU than encoding the same texts one call at a time.
    """
    model = _load_model()
    if model is None:
        return
    # Strip before keying: embedding_similarity strips its inputs, so cached
    # entries must be stored under the stripped text or lookups would miss.
    stripped = [t.strip() for t in texts]
    todo = [t for t in dict.fromkeys(stripped) if t and _cache_get(t) is None]
    if not todo:
        return
    vectors = model.encode(todo, normalize_embeddings=True, batch_size=8)
    for text, vec in zip(todo, vectors, strict=True):
        _cache_put(text, vec.tolist())


async def precompute_embeddings(texts: list[str]) -> None:
    """Batch-encode profile texts off-thread so later pair scoring hits cache.

    Used by the cold batch-score path: pre-encoding every unique candidate and
    project text in one batched call replaces N sequential ~10s encodes.
    No-op when embeddings are disabled/unavailable (fallback needs no cache).
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_ENCODE_EXECUTOR, _encode_many_sync, texts)


def _cosine_vectors(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return round(max(0.0, min(1.0, dot)), 4)


def _similarity_sync(a: str, b: str) -> tuple[float, str]:
    """Model load + both encodes + cosine, all inside one worker thread.

    Keeping everything in a single executor hop means the (possibly ~30s)
    model load and the CPU-heavy encodes never run on the event loop, and the
    two encodes don't contend for cores from separate threads.
    """
    vec_a = _encode_sync(a)
    vec_b = _encode_sync(b)
    if not vec_a or not vec_b:
        score = _fallback_similarity(a, b)
        return (
            score,
            f"Token-cosine fallback similarity = {score:.4f} "
            "(embedding model not loaded).",
        )
    score = _cosine_vectors(vec_a, vec_b)
    return (
        score,
        f"BGE embedding cosine similarity ({settings.BGE_MODEL_NAME}) = {score:.4f}.",
    )


async def embedding_similarity(text_a: str, text_b: str) -> tuple[float, str]:
    """Return (similarity 0-1, method description)."""
    a = text_a.strip()
    b = text_b.strip()
    if not a or not b:
        return 0.0, "Empty profile text; embedding similarity is 0.0."

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_ENCODE_EXECUTOR, _similarity_sync, a, b)


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
