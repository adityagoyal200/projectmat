"""Pins the single-flight guard on batch score computation.

A cold batch compute takes minutes (CPU embeddings). Before the guard, a user
reloading the page mid-run kicked off a second full compute that raced the
first — thrashing the CPU and double-writing cache rows (the observed
"backend hangs after I reload" failure). Concurrent requests for the same
batch must now run strictly one at a time; different batches stay independent.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.features.matching import service as matching_service
from app.features.matching.service import MatchService


@pytest.fixture(autouse=True)
def _fresh_locks(monkeypatch):
    monkeypatch.setattr(matching_service, "_batch_score_locks", {})


def _service_with_slow_inner(concurrency: dict) -> MatchService:
    svc = MatchService.__new__(MatchService)  # no DB needed

    async def _inner(batch_id: int, *, force: bool):
        concurrency["active"] += 1
        concurrency["peak"] = max(concurrency["peak"], concurrency["active"])
        await asyncio.sleep(0.02)  # stand-in for the minutes-long compute
        concurrency["active"] -= 1
        return f"result-{batch_id}"

    svc._compute_batch_scores_inner = AsyncMock(side_effect=_inner)
    return svc


@pytest.mark.anyio
async def test_same_batch_requests_are_serialized():
    concurrency = {"active": 0, "peak": 0}
    svc = _service_with_slow_inner(concurrency)

    results = await asyncio.gather(*(svc.compute_batch_scores(7) for _ in range(5)))

    assert results == ["result-7"] * 5
    assert concurrency["peak"] == 1  # never two computes for one batch at once


@pytest.mark.anyio
async def test_different_batches_do_not_block_each_other():
    concurrency = {"active": 0, "peak": 0}
    svc = _service_with_slow_inner(concurrency)

    await asyncio.gather(svc.compute_batch_scores(1), svc.compute_batch_scores(2))

    assert concurrency["peak"] == 2  # independent batches ran concurrently
