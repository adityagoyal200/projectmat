"""Extract developer profile URLs and usernames from parsed resume text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ExtractedProfiles:
    """Container for all developer profile handles found in a resume."""

    github_username: str | None = None
    github_repositories: list[str] = field(default_factory=list)
    leetcode_username: str | None = None
    codeforces_username: str | None = None
    scholar_id: str | None = None
    kaggle_username: str | None = None
    live_links: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)


# ── Regex patterns ────────────────────────────────────────────────────────────

_GITHUB_PATTERNS = [
    # github.com/username  (not github.com/orgs, github.com/settings, etc.)
    re.compile(
        r"github\.com/([A-Za-z0-9](?:[A-Za-z0-9\-]{0,37}[A-Za-z0-9])?)(?:[/\s?#]|$)",
        re.IGNORECASE,
    ),
]

_GITHUB_REPOSITORY_PATTERN = re.compile(
    r"https?://github\.com/"
    r"([A-Za-z0-9](?:[A-Za-z0-9\-]{0,37}[A-Za-z0-9])?)/"
    r"([A-Za-z0-9._\-]{1,100})"
    r"(?:[/\s?#]|$)",
    re.IGNORECASE,
)

_LEETCODE_PATTERNS = [
    re.compile(
        r"leetcode\.com/(?:u/)?([A-Za-z0-9_\-]{1,40})(?:[/\s?#]|$)",
        re.IGNORECASE,
    ),
]

_CODEFORCES_PATTERNS = [
    re.compile(
        r"codeforces\.com/profile/([A-Za-z0-9_.\-]{1,40})(?:[/\s?#]|$)",
        re.IGNORECASE,
    ),
]

_SCHOLAR_PATTERNS = [
    re.compile(
        r"scholar\.google\.com/citations\?.*?user=([A-Za-z0-9_\-]{8,20})",
        re.IGNORECASE,
    ),
]

_KAGGLE_PATTERNS = [
    re.compile(
        r"kaggle\.com/([A-Za-z0-9_\-]{1,40})(?:[/\s?#]|$)",
        re.IGNORECASE,
    ),
]

# URLs that look like deployed projects or personal sites.
_LIVE_LINK_PATTERN = re.compile(
    r"https?://(?!(?:github\.com|leetcode\.com|codeforces\.com|"
    r"scholar\.google|kaggle\.com|linkedin\.com|drive\.google))"
    r"[A-Za-z0-9\-]+\.[A-Za-z]{2,}[^\s\"'<>]*",
    re.IGNORECASE,
)

# Usernames we should skip (common GitHub org/page names, not real users)
_GITHUB_SKIP = frozenset(
    {
        "orgs",
        "settings",
        "features",
        "topics",
        "trending",
        "explore",
        "notifications",
        "marketplace",
        "pulls",
        "issues",
        "sponsors",
        "about",
        "pricing",
        "security",
        "login",
        "signup",
        "apps",
    }
)

_GITHUB_REPO_SKIP = frozenset(
    {
        "settings",
        "followers",
        "following",
        "repositories",
        "stars",
        "packages",
        "projects",
    }
)

_LEETCODE_SKIP = frozenset(
    {
        "accounts",
        "contest",
        "discuss",
        "explore",
        "problemset",
        "problems",
        "tag",
    }
)

_ACHIEVEMENT_LINE_PATTERN = re.compile(
    r"\b(award|winner|finalist|hackathon|publication|published|paper|patent|"
    r"scholarship|certification|certified|ranked|medal)\b",
    re.IGNORECASE,
)


def _first_match(patterns: list[re.Pattern], text: str) -> str | None:
    """Return the first capture group from the first matching pattern."""
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(1)
    return None


def _dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for raw in urls:
        url = raw.rstrip(".,;:)")
        key = url.lower().removesuffix("/")
        if key not in seen:
            seen.add(key)
            deduped.append(url)
    return deduped


def parse_username(url: str, domain: str) -> str | None:
    """Extract username from a profile URL for a specific domain."""
    if not url:
        return None

    url = url.strip()

    # 1. If it's already a clean username (no slashes, no dots)
    if "/" not in url and "." not in url and ":" not in url:
        return url

    import re

    # Capture the segment after the domain and optional /u/ or /profile/
    pattern = re.compile(rf"{domain}/(?:u/|profile/)?([A-Za-z0-9_.-]+)", re.IGNORECASE)
    match = pattern.search(url)
    if match:
        return match.group(1).strip("/")

    # Fallback: if domain is in URL, strip protocol and domain
    if domain in url.lower():
        clean = re.sub(
            rf"^https?://(?:www\.)?{re.escape(domain)}/?(?:u/|profile/)?",
            "",
            url,
            flags=re.IGNORECASE,
        )
        clean = clean.split("?")[0].split("#")[0].strip("/")
        if clean:
            return clean

    return None


def extract_profiles(text: str) -> ExtractedProfiles:
    """
    Scan resume text for developer profile URLs and return structured handles.

    Handles GitHub, LeetCode, Codeforces, Google Scholar, and Kaggle URLs.
    Also collects any other HTTP(S) links that look like deployed project sites.
    """
    result = ExtractedProfiles()

    # GitHub
    gh = _first_match(_GITHUB_PATTERNS, text)
    if gh and gh.lower() not in _GITHUB_SKIP:
        result.github_username = gh

    repositories: list[str] = []
    for match in _GITHUB_REPOSITORY_PATTERN.finditer(text):
        owner, repo = match.group(1), match.group(2)
        if owner.lower() in _GITHUB_SKIP or repo.lower() in _GITHUB_REPO_SKIP:
            continue
        repositories.append(f"https://github.com/{owner}/{repo}")
        if result.github_username is None:
            result.github_username = owner
    result.github_repositories = _dedupe_urls(repositories)

    # LeetCode
    leetcode = _first_match(_LEETCODE_PATTERNS, text)
    if leetcode and leetcode.lower() not in _LEETCODE_SKIP:
        result.leetcode_username = leetcode

    # Codeforces
    result.codeforces_username = _first_match(_CODEFORCES_PATTERNS, text)

    # Google Scholar
    result.scholar_id = _first_match(_SCHOLAR_PATTERNS, text)

    # Kaggle
    result.kaggle_username = _first_match(_KAGGLE_PATTERNS, text)

    # Live links (deployed project URLs)
    result.live_links = _dedupe_urls(
        [match.group(0) for match in _LIVE_LINK_PATTERN.finditer(text)]
    )

    achievements: list[str] = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip(" -*\t")
        if not clean or len(clean) > 240:
            continue
        if _ACHIEVEMENT_LINE_PATTERN.search(clean):
            achievements.append(clean)
    result.achievements = list(dict.fromkeys(achievements))[:12]

    return result
