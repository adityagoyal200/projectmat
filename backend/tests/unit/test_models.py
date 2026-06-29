from app.features.candidates.models import Candidate, CandidateDocument, CandidateSkill
from app.features.imports.models import ImportBatch, ImportFile, ImportValidationIssue
from app.features.mentors.models import Mentor
from app.features.projects.models import Project, ProjectPreference, ProjectPrerequisite
from app.features.shared.models import Skill


def test_import_batch_relationships():
    batch = ImportBatch(status="created")
    file = ImportFile(file_name="test.xlsx", file_type="workbook", batch=batch)
    issue = ImportValidationIssue(issue_type="error", message="bad row", batch=batch)
    candidate = Candidate(registration_number="123", name="John", import_batch=batch)

    assert file.batch is batch
    assert issue.batch is batch
    assert candidate.import_batch is batch


def test_candidate_relationships():
    candidate = Candidate(registration_number="123", name="John")
    doc = CandidateDocument(document_type="resume", candidate=candidate)
    skill = Skill(name="Python")
    cand_skill = CandidateSkill(candidate=candidate, skill=skill, source="resume")

    assert doc.candidate is candidate
    assert cand_skill.candidate is candidate
    assert cand_skill.skill is skill


def test_project_relationships():
    mentor = Mentor(name="Dr. Smith", email="smith@example.com")
    project = Project(title="AI Research", mentor=mentor)
    skill = Skill(name="Machine Learning")
    prereq = ProjectPrerequisite(project=project, skill=skill, is_required="true")

    pref = ProjectPreference(
        project=project, preference_type="student_selection", preference_value="123"
    )

    assert project.mentor is mentor
    assert prereq.project is project
    assert prereq.skill is skill
    assert pref.project is project
