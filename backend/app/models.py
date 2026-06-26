"""
Central hub for importing all SQLAlchemy models so that Alembic can discover them.
"""

from app.database import Base
from app.features.candidates.models import (
    Candidate,
    CandidateDocument,
    CandidateEmbedding,
    CandidateSkill,
)
from app.features.imports.models import ImportBatch, ImportFile, ImportValidationIssue
from app.features.matching.models import MatchResult, MatchResultExplanation, MatchRun
from app.features.mentors.models import Mentor
from app.features.projects.models import (
    Project,
    ProjectEmbedding,
    ProjectPreference,
    ProjectPrerequisite,
)

# Import all models here
from app.features.shared.models import AuditLog, Skill, Tag, Technology

__all__ = [
    "Base",
    "Skill",
    "Technology",
    "Tag",
    "AuditLog",
    "ImportBatch",
    "ImportFile",
    "ImportValidationIssue",
    "Mentor",
    "Project",
    "ProjectPrerequisite",
    "ProjectPreference",
    "ProjectEmbedding",
    "Candidate",
    "CandidateDocument",
    "CandidateSkill",
    "CandidateEmbedding",
    "MatchRun",
    "MatchResult",
    "MatchResultExplanation",
]
