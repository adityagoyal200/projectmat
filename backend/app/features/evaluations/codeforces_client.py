from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger()


async def fetch_codeforces_metrics(username: str) -> dict:
    """Fetch user rating, max rating, and rank from Codeforces API."""
    url = f"https://codeforces.com/api/user.info?handles={username}"
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
                    "codeforces.api_failed", username=username, status=resp.status_code
                )
                return {"fetch_error": f"HTTP_{resp.status_code}"}

            res = resp.json()
            if res.get("status") != "OK" or not res.get("result"):
                logger.warning("codeforces.user_not_found", username=username)
                return {"fetch_error": "UserNotFound"}

            user = res["result"][0]
            return {
                "rating": int(user.get("rating") or 0),
                "max_rating": int(user.get("maxRating") or 0),
                "rank": user.get("rank", "unrated"),
                "max_rank": user.get("maxRank", "unrated"),
                "problems_solved": 0,  # default placeholder, codeforces requires parsing submissions for solved count
            }
    except Exception as exc:
        logger.error("codeforces.fetch_exception", username=username, error=str(exc))
        return {"fetch_error": str(type(exc).__name__)}
