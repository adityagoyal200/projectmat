"""Unit tests for the embedding cache and batch precompute.

Uses a fake model so no real sentence-transformer (or its ~30s load) is
needed. Pins the invariant that precompute_embeddings fills the cache under
the *stripped* text — embedding_similarity strips its inputs, so a mismatch
would silently turn every "pre-warmed" lookup into a fresh ~10s CPU encode.
"""

import pytest

from app.features.matching import embeddings as emb


class _FakeVector:
    def __init__(self, values: list[float]):
        self._values = values

    def tolist(self) -> list[float]:
        return self._values


class _FakeModel:
    """Deterministic stand-in: unit vector per distinct text, call-counted."""

    def __init__(self):
        self.encode_calls: list[object] = []

    def encode(self, text_or_texts, normalize_embeddings=True, batch_size=None):
        self.encode_calls.append(text_or_texts)
        if isinstance(text_or_texts, list):
            return [self._vec(t) for t in text_or_texts]
        return self._vec(text_or_texts)

    @staticmethod
    def _vec(text: str) -> _FakeVector:
        return _FakeVector([1.0, float(len(text) % 7)])


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch):
    monkeypatch.setattr(emb, "_encode_cache", type(emb._encode_cache)())


@pytest.fixture
def fake_model(monkeypatch):
    model = _FakeModel()
    monkeypatch.setattr(emb, "_load_model", lambda: model)
    return model


@pytest.mark.anyio
async def test_precompute_fills_cache_under_stripped_keys(fake_model):
    await emb.precompute_embeddings(["  hello world  ", "other text"])
    # similarity strips its inputs; both lookups must hit the cache
    await emb.embedding_similarity("hello world", "other text")
    # exactly one model call: the batched precompute, no re-encodes after
    assert len(fake_model.encode_calls) == 1
    assert fake_model.encode_calls[0] == ["hello world", "other text"]


@pytest.mark.anyio
async def test_precompute_skips_already_cached_and_empty(fake_model):
    await emb.precompute_embeddings(["alpha"])
    await emb.precompute_embeddings(["alpha", "  ", "alpha", "beta"])
    # second call only encodes the genuinely new text
    assert fake_model.encode_calls[-1] == ["beta"]


@pytest.mark.anyio
async def test_similarity_uses_fallback_without_model(monkeypatch):
    monkeypatch.setattr(emb, "_load_model", lambda: None)
    score, detail = await emb.embedding_similarity(
        "python machine learning", "machine learning project"
    )
    assert 0.0 <= score <= 1.0
    assert "fallback" in detail.lower()


@pytest.mark.anyio
async def test_empty_text_short_circuits(fake_model):
    score, detail = await emb.embedding_similarity("   ", "something")
    assert score == 0.0
    assert not fake_model.encode_calls


def test_cache_evicts_oldest_beyond_cap(monkeypatch, fake_model):
    monkeypatch.setattr(emb, "_ENCODE_CACHE_MAX", 2)
    emb._encode_sync("one")
    emb._encode_sync("two")
    emb._encode_sync("three")  # evicts "one"
    assert emb._cache_get("one") is None
    assert emb._cache_get("two") is not None
    assert emb._cache_get("three") is not None
