from app.features.matching.scoring import (
    LlmScoreComponents,
    compute_hybrid_final_score,
    compute_preference_signal,
    compute_preliminary_score,
    compute_prerequisite_overlap,
    compute_resume_experience,
)


def test_tiered_prerequisite_overlap_family_credit():
    result = compute_prerequisite_overlap(
        candidate_skills=["PyTorch", "Python"],
        prerequisites=["TensorFlow", "SQL"],
    )
    # PyTorch family-matches TensorFlow at 0.5; SQL missing
    assert result.score == round(0.5 / 2, 4)
    assert any(d.tier == "family" for d in result.matched_details)


def test_prerequisite_overlap_exact_match():
    result = compute_prerequisite_overlap(
        candidate_skills=["Python", "Docker"],
        prerequisites=["Python", "PyTorch", "SQL"],
    )
    assert result.score == round(1.0 / 3, 4)


def test_resume_experience_not_prereq_keywords():
    result = compute_resume_experience(
        resume_text="Experience: Built a computer vision pipeline. Developed APIs.",
        project_abstract="Research on vision systems and deployment",
        prerequisites=["Python"],
    )
    assert result.score > 0
    assert result.project_mentions >= 1


def test_preliminary_score_range():
    prereq = compute_prerequisite_overlap(["Python"], ["Python"])
    resume = compute_resume_experience(
        "Experience section with built systems", "AI project", []
    )
    score = compute_preliminary_score(
        embedding_similarity=0.8,
        prerequisite_overlap=prereq,
        resume_experience=resume,
    )
    assert 0.0 <= score <= 1.0


def test_hybrid_score_weights_growth_potential():
    hybrid = compute_hybrid_final_score(
        embedding_similarity=0.5,
        embedding_detail="test",
        prerequisite_overlap=compute_prerequisite_overlap(["Python"], ["Python"]),
        resume_experience=compute_resume_experience(
            "Experience: built X", "AI", ["Python"]
        ),
        preference_signal=compute_preference_signal("X", []),
        llm_scores=LlmScoreComponents(
            readiness=0.5,
            growth_potential=0.95,
            interest=0.6,
            semantic_fit=0.7,
        ),
    )
    assert hybrid.growth_potential == 0.95
    assert hybrid.llm_evaluated is True
    assert (
        hybrid.weighted_contributions["growth_potential"]
        > hybrid.weighted_contributions["readiness"]
    )


def test_hybrid_without_llm():
    hybrid = compute_hybrid_final_score(
        embedding_similarity=0.6,
        embedding_detail="test",
        prerequisite_overlap=compute_prerequisite_overlap(["Python"], ["Python"]),
        resume_experience=compute_resume_experience("Experience", "AI", []),
        preference_signal=compute_preference_signal("X", []),
        llm_scores=None,
    )
    assert hybrid.llm_evaluated is False
    assert hybrid.readiness == 0.0
    assert hybrid.growth_potential == 0.0
