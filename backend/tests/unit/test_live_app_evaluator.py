import httpx
import pytest

from app.features.evaluations.live_app_evaluator import evaluate_live_app


@pytest.mark.anyio
async def test_live_app_evaluator_scores_healthy_html():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<html><head><title>Demo App</title></head><body>Ready</body></html>",
            request=request,
        )
    )

    async with httpx.AsyncClient(transport=transport) as client:
        result = await evaluate_live_app(
            "https://demo.example.app",
            client=client,
            timeout_seconds=5,
        )

    assert result.status == "completed"
    assert result.http_status == 200
    assert result.score >= 0.9
    assert result.metrics["title"] == "Demo App"
    assert len(result.agent_trace) >= 2


@pytest.mark.anyio
async def test_live_app_evaluator_flags_runtime_error_text():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<html><title>Oops</title><body>Application error</body></html>",
            request=request,
        )
    )

    async with httpx.AsyncClient(transport=transport) as client:
        result = await evaluate_live_app(
            "https://demo.example.app",
            client=client,
            timeout_seconds=5,
        )

    assert result.status == "completed_with_errors"
    assert any(f["code"] == "visible_runtime_error" for f in result.findings)


@pytest.mark.anyio
async def test_live_app_evaluator_rejects_invalid_url():
    result = await evaluate_live_app("not-a-url")

    assert result.status == "invalid_url"
    assert result.score == 0.0
    assert result.findings[0]["code"] == "invalid_url"
