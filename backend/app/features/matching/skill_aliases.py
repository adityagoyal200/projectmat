"""Skill normalization, aliases, and adjacent-skill families.

Used for tiered prerequisite matching.
"""

from __future__ import annotations

import re

# Maps common aliases / abbreviations to canonical tokens (lowercase).
SKILL_ALIASES: dict[str, str] = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "ml": "machine learning",
    "dl": "deep learning",
    "cv": "computer vision",
    "nlp": "natural language processing",
    "ai": "artificial intelligence",
    "postgres": "postgresql",
    "psql": "postgresql",
    "tf": "tensorflow",
    "pt": "pytorch",
    "k8s": "kubernetes",
    "node": "node.js",
    "nodejs": "node.js",
    "reactjs": "react",
    "vuejs": "vue",
    # Cloud / DevOps expansions
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "google cloud": "gcp",
    "microsoft azure": "azure",
    # LLM / GenAI expansions
    "large language model": "llm",
    "large language models": "llm",
    "llms": "llm",
    "generative ai": "llm",
    "genai": "llm",
    "gen-ai": "llm",
    "langchain": "llm",
    "openai": "llm",
    "chatgpt": "llm",
    "gpt": "llm",
    # Data science
    "data science": "data analysis",
    "data analytics": "data analysis",
    "r programming": "r",
    # Web
    "express": "node.js",
    "expressjs": "node.js",
    "nextjs": "react",
    "next.js": "react",
    "flask": "python",
    "django": "python",
    "fastapi": "python",
}

# Skills in the same family can partially satisfy a prerequisite (0.5 credit).
SKILL_FAMILIES: list[frozenset[str]] = [
    frozenset({"pytorch", "tensorflow", "keras", "deep learning", "machine learning"}),
    frozenset({"python", "numpy", "pandas", "scikit-learn", "scikit learn"}),
    frozenset({"postgresql", "sql", "mysql", "mongodb", "database"}),
    frozenset({"react", "vue", "angular", "javascript", "typescript", "frontend"}),
    frozenset({"docker", "kubernetes", "aws", "azure", "gcp", "devops", "cloud"}),
    frozenset({"computer vision", "opencv", "image processing"}),
    frozenset(
        {"natural language processing", "nlp", "transformers", "llm", "huggingface"}
    ),
    frozenset({"java", "c++", "c#", "programming"}),
    frozenset({"r", "statistics", "data analysis"}),
    frozenset({"machine learning", "deep learning", "llm", "artificial intelligence"}),
    frozenset({"git", "github", "version control"}),
    frozenset({"linux", "shell", "bash", "unix"}),
]

# Tokens that are too generic to count as skill keywords when extracted
# from multi-word prerequisites.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "to",
        "in",
        "of",
        "for",
        "with",
        "on",
        "is",
        "it",
        "be",
        "at",
        "by",
        "from",
        "as",
        "into",
        "via",
        "basic",
        "advanced",
        "intermediate",
        "understanding",
        "knowledge",
        "experience",
        "skills",
        "ability",
        "learn",
        "learning",
        "eager",
        "willing",
        "good",
        "strong",
        "some",
        "any",
        "familiarity",
        "familiar",
        "development",
        "concepts",
        "fundamentals",
        "proficiency",
        "proficient",
        "flow",
        "logic",
        "native",
    }
)

MatchTier = str  # "exact" | "alias" | "family" | "missing"


def normalize_skill(name: str) -> str:
    token = name.lower().strip()
    return SKILL_ALIASES.get(token, token)


def _families_for(skill: str) -> list[frozenset[str]]:
    """Return ALL families a skill belongs to."""
    normalized = normalize_skill(skill)
    return [family for family in SKILL_FAMILIES if normalized in family]


def _skills_share_family(skill_a: str, skill_b: str) -> bool:
    """Check if two skills share any family (after normalization)."""
    families_a = _families_for(skill_a)
    if not families_a:
        return False
    norm_b = normalize_skill(skill_b)
    return any(norm_b in family for family in families_a)


def _extract_meaningful_tokens(text: str) -> list[str]:
    """Extract meaningful skill tokens from a natural-language prerequisite phrase.

    Filters out stopwords and very short tokens, then returns normalized tokens.
    """
    raw_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]{1,}", text.lower().strip())
    return [
        normalize_skill(t) for t in raw_tokens if t not in _STOPWORDS and len(t) >= 2
    ]


def prereq_match_credit(
    candidate_skills: list[str], prerequisite: str
) -> tuple[float, MatchTier, str | None]:
    """
    Return (credit 0.0-1.0, tier, matched_skill_name).
    - exact/alias: 1.0
    - family: 0.5
    - token: 0.5  (significant token from a multi-word prereq matched)
    - missing: 0.0
    """
    prereq_norm = normalize_skill(prerequisite)
    normalized_candidates = [(s, normalize_skill(s)) for s in candidate_skills]

    # --- Pass 1: Exact / alias match (full string) ---
    for original, norm in normalized_candidates:
        if prereq_norm == norm:
            tier: MatchTier = (
                "alias" if normalize_skill(original) != prereq_norm else "exact"
            )
            return 1.0, tier, original

    # --- Pass 2: Family match (full prerequisite vs each candidate skill) ---
    for original, _ in normalized_candidates:
        if _skills_share_family(prerequisite, original):
            return 0.5, "family", original

    # --- Pass 3: Token-level match for multi-word prerequisites ---
    # Extract meaningful tokens from the prerequisite phrase and check
    # if any match a candidate skill exactly (after normalization).
    prereq_tokens = _extract_meaningful_tokens(prerequisite)
    candidate_norm_set = {norm for _, norm in normalized_candidates}

    for token in prereq_tokens:
        if token in candidate_norm_set:
            # Find the original skill name
            for original, norm in normalized_candidates:
                if norm == token:
                    return 0.5, "alias", original
            break

    # Also check token-level family matches
    for token in prereq_tokens:
        for original, _ in normalized_candidates:
            if _skills_share_family(token, original):
                return 0.5, "family", original

    return 0.0, "missing", None
