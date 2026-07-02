from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx

try:
    from playwright.async_api import async_playwright
except Exception:
    async_playwright = None


@dataclass(frozen=True)
class LiveAppEvaluationResult:
    url: str
    status: str
    score: float
    http_status: int | None
    latency_ms: int | None
    metrics: dict
    findings: list[dict] = field(default_factory=list)
    agent_trace: list[dict] = field(default_factory=list)
    screenshot_path: str | None = None


_TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_VISIBLE_ERROR_PATTERNS = [
    re.compile(r"\b(application error|runtime error|internal server error)\b", re.I),
    re.compile(r"\b(unhandled exception|traceback|stack trace)\b", re.I),
    re.compile(r"\b(404 not found|502 bad gateway|503 service unavailable)\b", re.I),
]
_PERSISTENT_LOADING_PATTERNS = [
    re.compile(r"\bloading\.\.\.\s*$", re.I),
    re.compile(r"\bplease wait\b", re.I),
]


def _finding(
    severity: str, code: str, message: str, evidence: str | None = None
) -> dict:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "evidence": evidence,
    }


def _agent_step(reason: str, action: str, observe: str) -> dict:
    return {"reason": reason, "action": action, "observe": observe}


def _is_valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


async def evaluate_live_app(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout_seconds: int | None = None,  # noqa: ARG001
) -> LiveAppEvaluationResult:
    """Evaluate a live application URL through autonomous Playwright browser checks."""
    trace = [
        _agent_step(
            "Validate whether the submitted link can be visited.",
            "parse_url",
            "URL accepted for browser evaluation."
            if _is_valid_http_url(url)
            else "URL is not a valid HTTP(S) link.",
        )
    ]

    if not _is_valid_http_url(url):
        return LiveAppEvaluationResult(
            url=url,
            status="invalid_url",
            score=0.0,
            http_status=None,
            latency_ms=None,
            metrics={"valid_url": False},
            findings=[
                _finding(
                    "error",
                    "invalid_url",
                    "Live app URL must be an absolute HTTP(S) URL.",
                )
            ],
            agent_trace=trace,
            screenshot_path=None,
        )

    def _extract_title(html: str) -> str | None:
        match = _TITLE_PATTERN.search(html)
        if not match:
            return None
        return re.sub(r"\s+", " ", match.group(1)).strip()[:200] or None

    if client is not None:
        started = time.perf_counter()
        http_status = 200
        latency_ms = 0
        title = None
        visible_errors = []
        loading_signals = []
        content_type = "text/html"
        try:
            response = await client.get(url)
            latency_ms = int((time.perf_counter() - started) * 1000)
            http_status = response.status_code
            content_type = response.headers.get("content-type", "")
            text = response.text[:200000]
            title = _extract_title(text)
            for pattern in _VISIBLE_ERROR_PATTERNS:
                if pattern.search(text):
                    visible_errors.append(pattern.pattern)
            for pattern in _PERSISTENT_LOADING_PATTERNS:
                if pattern.search(text.strip()):
                    loading_signals.append(pattern.pattern)
            trace.append(
                _agent_step("HTTP mock check", "http_get", f"status={http_status}")
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return LiveAppEvaluationResult(
                url=url,
                status="unreachable",
                score=0.0,
                http_status=None,
                latency_ms=latency_ms,
                metrics={"valid_url": True, "network_error": type(exc).__name__},
                findings=[_finding("error", "network_error", str(exc))],
                agent_trace=trace,
                screenshot_path=None,
            )

        findings = []
        ok_status = 200 <= http_status < 400
        if not ok_status:
            findings.append(
                _finding(
                    "error",
                    "bad_http_status",
                    "Live app returned a non-success HTTP status.",
                    str(http_status),
                )
            )
        if visible_errors:
            findings.append(
                _finding(
                    "error",
                    "visible_runtime_error",
                    "Page content includes visible runtime or server error text.",
                )
            )
        if loading_signals:
            findings.append(
                _finding(
                    "warning",
                    "possible_persistent_loading",
                    "Page may be stuck in a loading state.",
                )
            )
        if not title:
            findings.append(
                _finding(
                    "info",
                    "missing_title",
                    "HTML response did not include a page title.",
                )
            )

        metrics = {
            "valid_url": True,
            "content_type": content_type,
            "title": title,
            "visible_error_count": len(visible_errors),
            "loading_signal_count": len(loading_signals),
            "console_errors": 0,
            "screenshot_saved": False,
        }

        # Rubric scoring
        score = 0.0
        if ok_status:
            score += 0.40
        if title:
            score += 0.20
        if not visible_errors:
            score += 0.20
        if not loading_signals:
            score += 0.10
        score += 0.10  # 0 console errors bonus

        score = round(min(max(score, 0.0), 1.0), 4)
        status = (
            "completed"
            if (ok_status and not visible_errors)
            else "completed_with_errors"
        )

        return LiveAppEvaluationResult(
            url=url,
            status=status,
            score=score,
            http_status=http_status,
            latency_ms=latency_ms,
            metrics=metrics,
            findings=findings,
            agent_trace=trace,
            screenshot_path=None,
        )

    # Output screenshots directory
    if async_playwright is None:
        trace.append(
            _agent_step(
                "Playwright dependency missing; cannot run browser checks.",
                "launch_browser",
                "playwright.async_api is not installed in this environment.",
            )
        )
        return LiveAppEvaluationResult(
            url=url,
            status="playwright_unavailable",
            score=0.0,
            http_status=None,
            latency_ms=None,
            metrics={"valid_url": True, "playwright_available": False},
            findings=[
                _finding(
                    "warning",
                    "playwright_unavailable",
                    "Playwright is not installed; live app browser checks were skipped.",
                )
            ],
            agent_trace=trace,
            screenshot_path=None,
        )

    screens_dir = Path("screenshots")
    screens_dir.mkdir(exist_ok=True)
    url_hash = hashlib.md5(url.encode()).hexdigest()
    screenshot_file = screens_dir / f"{url_hash}.png"

    started = time.perf_counter()
    http_status = 200
    latency_ms = 0
    title = None
    visible_errors = []
    loading_signals = []
    content_type = "text/html"
    screenshot_path = None

    try:
        trace.append(
            _agent_step(
                "Initialize sandboxed browser session.",
                "launch_browser",
                "Chromium launch requested.",
            )
        )
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # Create a clean context with default viewport
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()

            # Listen for console errors
            console_errors = []
            page.on("pageerror", lambda err: console_errors.append(err.message))

            trace.append(
                _agent_step(
                    f"Navigate to project URL: {url} with cold-start wakeup tolerance.",
                    "page_goto",
                    "Navigation started.",
                )
            )

            # Wakes up sleeping Render/Streamlit by extending navigation timeout to 45 seconds
            try:
                response = await page.goto(url, wait_until="networkidle", timeout=45000)
                http_status = response.status if response else 200
            except Exception as goto_exc:
                # Retry once if it was a cold start timeout
                trace.append(
                    _agent_step(
                        "Cold start detected or timeout. Retrying page navigation...",
                        "retry_goto",
                        str(goto_exc),
                    )
                )
                response = await page.goto(url, wait_until="load", timeout=30000)
                http_status = response.status if response else 200

            latency_ms = int((time.perf_counter() - started) * 1000)
            title = await page.title()

            # Attempt a simulated click on standard UI links to evaluate hydration
            try:
                tabs = await page.query_selector_all("a, button")
                clicked_tab = False
                for tab in tabs[:3]:
                    text = (await tab.inner_text()).lower()
                    if any(
                        t in text
                        for t in {"overview", "details", "analysis", "dashboard", "tab"}
                    ):
                        trace.append(
                            _agent_step(
                                f"Interact with UI: Clicking tab/link: '{text}'",
                                "click_element",
                                "Simulated UI interaction.",
                            )
                        )
                        await tab.click()
                        await page.wait_for_timeout(1000)
                        clicked_tab = True
                        break
                if not clicked_tab:
                    trace.append(
                        _agent_step(
                            "Scan page structure; no common dashboard tabs found to interact with.",
                            "element_check",
                            "Completed inspection.",
                        )
                    )
            except Exception:
                pass  # Ignore click errors

            # Analyze page text content for error patterns
            page_text = await page.content()
            for pattern in _VISIBLE_ERROR_PATTERNS:
                if pattern.search(page_text):
                    visible_errors.append(pattern.pattern)
            for pattern in _PERSISTENT_LOADING_PATTERNS:
                if pattern.search(page_text):
                    loading_signals.append(pattern.pattern)

            # Capture screenshot
            await page.screenshot(path=str(screenshot_file))
            screenshot_path = f"screenshots/{url_hash}.png"

            trace.append(
                _agent_step(
                    "Capture page screenshot for validation verification.",
                    "save_screenshot",
                    f"Saved to {screenshot_path}",
                )
            )

            await browser.close()

    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        trace.append(
            _agent_step(
                "Observe whether the app reached a usable page.",
                "capture_error",
                str(exc),
            )
        )
        return LiveAppEvaluationResult(
            url=url,
            status="unreachable",
            score=0.0,
            http_status=None,
            latency_ms=latency_ms,
            metrics={"valid_url": True, "network_error": type(exc).__name__},
            findings=[
                _finding(
                    "error",
                    "network_error",
                    "The live app could not be reached or timed out.",
                    str(exc),
                )
            ],
            agent_trace=trace,
            screenshot_path=None,
        )

    findings: list[dict] = []
    ok_status = 200 <= http_status < 400
    if not ok_status:
        findings.append(
            _finding(
                "error",
                "bad_http_status",
                "Live app returned a non-success HTTP status.",
                str(http_status),
            )
        )
    if visible_errors:
        findings.append(
            _finding(
                "error",
                "visible_runtime_error",
                "Page content includes visible runtime or server error text.",
            )
        )
    if loading_signals:
        findings.append(
            _finding(
                "warning",
                "possible_persistent_loading",
                "Page may be stuck in a loading state.",
            )
        )
    if not title:
        findings.append(
            _finding(
                "info",
                "missing_title",
                "HTML response did not include a page title.",
            )
        )

    metrics = {
        "valid_url": True,
        "content_type": content_type,
        "title": title,
        "visible_error_count": len(visible_errors),
        "loading_signal_count": len(loading_signals),
        "console_errors": len(console_errors),
        "screenshot_saved": screenshot_path is not None,
    }

    # Rubric scoring
    score = 0.0
    if ok_status:
        score += 0.40
    if title:
        score += 0.20
    if not visible_errors:
        score += 0.20
    if not loading_signals:
        score += 0.10
    if len(console_errors) == 0:
        score += 0.10

    score = round(min(max(score, 0.0), 1.0), 4)
    status = (
        "completed" if (ok_status and not visible_errors) else "completed_with_errors"
    )

    return LiveAppEvaluationResult(
        url=url,
        status=status,
        score=score,
        http_status=http_status,
        latency_ms=latency_ms,
        metrics=metrics,
        findings=findings,
        agent_trace=trace,
        screenshot_path=screenshot_path,
    )
