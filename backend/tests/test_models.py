from app.models import (
    Base,
    Candidate,
    ImportBatch,
    MatchResult,
    MatchResultExplanation,
    MatchRun,
    Mentor,
    Project,
    ProjectPrerequisite,
    Skill,
)


def test_models_importable():
    """Ensure all models are imported correctly without circular dependencies."""
    assert Base is not None
    assert Skill is not None


def test_mentor_project_relationship():
    """Test 1:1 mentor to project relationship."""
    mentor = Mentor(name="John Doe", email="john@example.com")
    project = Project(title="AI Research", mentor=mentor)

    assert project.mentor == mentor
    assert mentor.project == project


def test_candidate_relationships():
    """Test candidate relationships with import batches and other entities."""
    batch = ImportBatch(status="pending")
    candidate = Candidate(
        registration_number="REG123", name="Alice", import_batch=batch
    )

    assert candidate.import_batch == batch
    assert candidate in batch.candidates


def test_project_relationships():
    """Test project relationships with prerequisites."""
    project = Project(title="Cool Project")
    skill = Skill(name="Python")
    prereq = ProjectPrerequisite(project=project, skill=skill, is_required="true")

    assert prereq in project.prerequisites
    assert prereq.skill == skill


def test_matching_relationships():
    """Test matching relationship structures."""
    run = MatchRun(status="completed")
    # Setting up dummy ids since we don't commit to DB in this unit test
    result = MatchResult(run=run, final_score=95.5)
    explanation = MatchResultExplanation(result=result, explanation_text="Good fit")

    assert result in run.results
    assert result.explanation == explanation
    assert explanation.result == result
