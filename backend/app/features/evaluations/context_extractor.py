from __future__ import annotations

import json
import re

import httpx
import structlog

from app.config import settings
from app.features.matching.llm_client import generate_chat_completion

logger = structlog.get_logger()


def convert_gdoc_to_export_url(url: str) -> str | None:
    """Convert a standard public Google Doc URL into a plain text export URL."""
    # Matches https://docs.google.com/document/d/<id>/...
    match = re.search(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        return None
    doc_id = match.group(1)
    return f"https://docs.google.com/document/d/{doc_id}/export?format=txt"


async def fetch_gdoc_text(export_url: str) -> str | None:
    """Fetch raw text content of a public Google Doc."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                export_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                },
            )
            if resp.status_code == 200:
                return resp.text
            logger.warning(
                "context_extractor.gdoc_fetch_failed",
                url=export_url,
                status=resp.status_code,
            )
    except Exception as exc:
        logger.error(
            "context_extractor.gdoc_fetch_exception", url=export_url, error=str(exc)
        )
    return None


async def extract_project_requirements(
    abstract: str | None, problem_statement_link: str | None
) -> dict:
    """Agent 1: Extract project features, tools, and prerequisites from Google Doc or abstract."""
    raw_text = None
    if problem_statement_link:
        export_url = convert_gdoc_to_export_url(problem_statement_link)
        if export_url:
            raw_text = await fetch_gdoc_text(export_url)

    if not raw_text:
        raw_text = abstract or ""

    if not raw_text.strip():
        return {"features": [], "technologies": [], "prerequisites": []}

    prompt = f"""Analyze the following project description or problem statement.
Extract:
1. Core features requested (list of key features).
2. Technologies/frameworks required.
3. Prerequisite skills needed by candidates.

Return the result as a strict, clean JSON object ONLY, with no wrapping markdown or backticks. Format:
{{
  "features": ["feature 1", "feature 2"],
  "technologies": ["tech 1", "tech 2"],
  "prerequisites": ["skill 1", "skill 2"]
}}

Document Text:
{raw_text[:4000]}
"""

    try:
        # Request completion (force if settings allow it, or fallback)
        res = await generate_chat_completion(
            prompt,
            system_prompt="You are a precise technical context extractor that returns strict JSON.",
            force=settings.LLM_ENABLED,
        )

        content = res.content.strip()
        if not content:
            # Fallback to simple deterministic extraction
            return extract_deterministic_fallback(raw_text)

        # Strip any markdown formatting (e.g. ```json ... ```)
        content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE)
        content = re.sub(r"```$", "", content, flags=re.IGNORECASE).strip()

        parsed = json.loads(content)
        return {
            "features": list(parsed.get("features") or []),
            "technologies": list(parsed.get("technologies") or []),
            "prerequisites": list(parsed.get("prerequisites") or []),
        }
    except Exception as exc:
        logger.warning(
            "context_extractor.llm_parse_failed",
            error=str(exc),
            fallback_active=True,
        )
        return extract_deterministic_fallback(raw_text)


def extract_deterministic_fallback(text: str) -> dict:
    """Fast, deterministic fallback when LLM fails or is disabled."""
    # Split text into sentences and search for keywords
    features = []

    words = re.findall(r"\b[A-Za-z0-9+#.-]+\b", text)
    tech_keywords = {
        "python",
        "react",
        "vue",
        "angular",
        "fastapi",
        "django",
        "flask",
        "postgres",
        "sqlite",
        "docker",
        "kubernetes",
        "node",
        "typescript",
        "javascript",
        "pytorch",
        "tensorflow",
        "r",
        "shiny",
    }

    found_techs = set()
    for w in words:
        wl = w.lower()
        if wl in tech_keywords:
            found_techs.add(w)

    # Extract sentences with action verbs as features
    sentences = re.split(r"[.!?]", text)
    for s in sentences:
        s_clean = s.strip()
        if 10 < len(s_clean) < 150 and any(
            verb in s_clean.lower()
            for verb in {"implement", "build", "create", "develop", "visualize"}
        ):
            features.append(s_clean)

    return {
        "features": features[:4],
        "technologies": list(found_techs),
        "prerequisites": list(found_techs),
    }
