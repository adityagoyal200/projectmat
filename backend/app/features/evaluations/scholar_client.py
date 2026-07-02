from __future__ import annotations

import re

import httpx
import structlog

logger = structlog.get_logger()


async def fetch_scholar_metrics(scholar_id: str) -> dict:
    """Fetch Citations, h-index, and publications count from Google Scholar profile."""
    url = f"https://scholar.google.com/citations?user={scholar_id}&hl=en"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                },
            )
            if resp.status_code != 200:
                logger.warning(
                    "scholar.api_failed", scholar_id=scholar_id, status=resp.status_code
                )
                return {"fetch_error": f"HTTP_{resp.status_code}"}

            html = resp.text

            # Extract Citations
            citations_match = re.search(
                r'Citations</a></td><td class="gsc_rsb_std">(\d+)</td>', html
            )
            citations = int(citations_match.group(1)) if citations_match else 0

            # Extract h-index
            hindex_match = re.search(
                r'h-index</a></td><td class="gsc_rsb_std">(\d+)</td>', html
            )
            hindex = int(hindex_match.group(1)) if hindex_match else 0

            # Extract Publication Count (items with class "gsc_a_at")
            publications = len(re.findall(r'class="gsc_a_at"', html))

            return {
                "citations": citations,
                "h_index": hindex,
                "publications": publications,
            }
    except Exception as exc:
        logger.error("scholar.fetch_exception", scholar_id=scholar_id, error=str(exc))
        return {"fetch_error": str(type(exc).__name__)}
