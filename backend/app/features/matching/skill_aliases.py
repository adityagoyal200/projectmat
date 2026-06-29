"""Skill normalization, aliases, and adjacent-skill families.

Used for tiered prerequisite matching.
"""

from __future__ import annotations

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
}

# Skills in the same family can partially satisfy a prerequisite (0.5 credit).
SKILL_FAMILIES: list[frozenset[str]] = [
    frozenset({"pytorch", "tensorflow", "keras", "deep learning", "machine learning"}),
    frozenset({"python", "numpy", "pandas", "scikit-learn", "scikit learn"}),
    frozenset({"postgresql", "sql", "mysql", "mongodb", "database"}),
    frozenset({"react", "vue", "angular", "javascript", "typescript", "frontend"}),
    frozenset({"docker", "kubernetes", "aws", "azure", "gcp", "devops"}),
    frozenset({"computer vision", "opencv", "image processing"}),
    frozenset({"natural language processing", "nlp", "transformers", "llm"}),
    frozenset({"java", "c++", "c#", "programming"}),
    frozenset({"r", "statistics", "data analysis"}),
]

MatchTier = str  # "exact" | "alias" | "family" | "missing"


def normalize_skill(name: str) -> str:
    token = name.lower().strip()
    return SKILL_ALIASES.get(token, token)


def _family_for(skill: str) -> frozenset[str] | None:
    normalized = normalize_skill(skill)
    for family in SKILL_FAMILIES:
        if normalized in family:
            return family
    return None


def prereq_match_credit(
    candidate_skills: list[str], prerequisite: str
) -> tuple[float, MatchTier, str | None]:
    """
    Return (credit 0.0-1.0, tier, matched_skill_name).
    - exact/alias: 1.0
    - family: 0.5
    - missing: 0.0
    """
    prereq_norm = normalize_skill(prerequisite)
    normalized_candidates = [(s, normalize_skill(s)) for s in candidate_skills]

    for original, norm in normalized_candidates:
        if prereq_norm == norm or prereq_norm in norm or norm in prereq_norm:
            tier: MatchTier = (
                "alias" if normalize_skill(original) != prereq_norm else "exact"
            )
            return 1.0, tier, original

    prereq_family = _family_for(prerequisite)
    if prereq_family:
        for original, _ in normalized_candidates:
            cand_family = _family_for(original)
            if cand_family is prereq_family or (
                cand_family and cand_family & prereq_family
            ):
                return 0.5, "family", original

    return 0.0, "missing", None
