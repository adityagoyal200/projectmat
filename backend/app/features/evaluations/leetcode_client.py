from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger()


async def fetch_leetcode_metrics(username: str) -> dict:
    """Fetch detailed LeetCode profile metrics using GraphQL."""
    url = "https://leetcode.com/graphql"
    query = """
    query userCombinedStats($username: String!) {
        matchedUser(username: $username) {
            submitStatsGlobal {
                acSubmissionNum {
                    difficulty
                    count
                }
            }
        }
        userContestRanking(username: $username) {
            attendedContestsCount
            rating
            globalRanking
            topPercentage
        }
    }
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json={"query": query, "variables": {"username": username}},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code != 200:
                logger.warning(
                    "leetcode.api_failed", username=username, status=resp.status_code
                )
                return {"fetch_error": f"HTTP_{resp.status_code}"}

            res = resp.json()
            data = res.get("data", {})
            user_data = data.get("matchedUser")
            if not user_data:
                logger.warning("leetcode.user_not_found", username=username)
                return {"fetch_error": "UserNotFound"}

            stats = user_data.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
            solved_map = {}
            for item in stats:
                difficulty = item.get("difficulty", "").lower()
                count = int(item.get("count") or 0)
                solved_map[difficulty] = count

            contest_data = data.get("userContestRanking") or {}
            contest_count = int(contest_data.get("attendedContestsCount") or 0)
            contest_rating = float(contest_data.get("rating") or 0.0)

            return {
                "total_solved": solved_map.get("all", 0),
                "easy_solved": solved_map.get("easy", 0),
                "medium_solved": solved_map.get("medium", 0),
                "hard_solved": solved_map.get("hard", 0),
                "contest_count": contest_count,
                "contest_rating": contest_rating,
            }
    except Exception as exc:
        logger.error("leetcode.fetch_exception", username=username, error=str(exc))
        return {"fetch_error": str(type(exc).__name__)}
