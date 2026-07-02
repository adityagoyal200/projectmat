from __future__ import annotations

from urllib.parse import urlparse

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


def parse_github_repository_url(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    return parts[0], parts[1].removesuffix(".git")


async def fetch_github_user_metrics(username: str) -> dict:
    """Fetch public GitHub user metrics and public PR contributions when credentials allow it."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ProjectMatchAI-Phase6/1.0",
    }
    if settings.GITHUB_TOKEN.strip():
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN.strip()}"

    try:
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            # Fetch user profile
            user_response = await client.get(f"https://api.github.com/users/{username}")
            user_response.raise_for_status()
            user = user_response.json()

            # Fetch user public repos
            repos_response = await client.get(
                f"https://api.github.com/users/{username}/repos",
                params={"per_page": 100, "sort": "updated"},
            )
            repos_response.raise_for_status()
            repos = repos_response.json()

            # Query public PRs authored by candidate
            pr_total = 0
            pr_merged = 0
            os_contrib_repos = set()
            os_contrib_stars = 0
            try:
                # All public PRs
                pr_resp = await client.get(
                    "https://api.github.com/search/issues",
                    params={"q": f"author:{username} type:pr is:public"},
                )
                if pr_resp.status_code == 200:
                    pr_data = pr_resp.json()
                    pr_total = pr_data.get("total_count", 0)
                    # Parse unique repos contributed to
                    for item in pr_data.get("items", []):
                        rep_url = item.get("repository_url")
                        if rep_url:
                            parts = rep_url.split("/repos/")
                            if len(parts) > 1:
                                repo_name = parts[1]
                                # Only count as OS if it's not the user's own repo
                                if not repo_name.lower().startswith(
                                    username.lower() + "/"
                                ):
                                    os_contrib_repos.add(repo_name)

                # Merged public PRs
                merged_resp = await client.get(
                    "https://api.github.com/search/issues",
                    params={"q": f"author:{username} type:pr is:merged"},
                )
                if merged_resp.status_code == 200:
                    pr_merged = merged_resp.json().get("total_count", 0)

                # Fetch stars for up to 3 OS contribution target repos to gauge impact
                for repo_name in list(os_contrib_repos)[:3]:
                    r_resp = await client.get(
                        f"https://api.github.com/repos/{repo_name}"
                    )
                    if r_resp.status_code == 200:
                        os_contrib_stars = max(
                            os_contrib_stars,
                            int(r_resp.json().get("stargazers_count") or 0),
                        )
            except Exception:
                pass  # Fail gracefully on PR search rate limit issues

        total_stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos)
        total_forks = sum(int(repo.get("forks_count") or 0) for repo in repos)
        recent_activity = sum(1 for repo in repos if repo.get("pushed_at"))

        # Extract top 10 public repositories (preferring original/non-forks)
        non_forks = [repo for repo in repos if not repo.get("fork")]
        source_repos = non_forks if non_forks else repos
        source_repos.sort(
            key=lambda r: (
                int(r.get("stargazers_count") or 0),
                int(r.get("forks_count") or 0),
                r.get("updated_at") or "",
            ),
            reverse=True,
        )
        repo_urls = [r.get("html_url") for r in source_repos[:10] if r.get("html_url")]

        return {
            "public_repos": int(user.get("public_repos") or 0),
            "followers": int(user.get("followers") or 0),
            "following": int(user.get("following") or 0),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "recent_activity_count": recent_activity,
            "pr_total_count": pr_total,
            "pr_merged_count": pr_merged,
            "os_contribution_count": len(os_contrib_repos),
            "max_os_repo_stars": os_contrib_stars,
            "repository_urls": repo_urls,
        }
    except Exception as exc:
        logger.error("github.fetch_exception", username=username, error=str(exc))
        return {"fetch_error": str(type(exc).__name__)}
