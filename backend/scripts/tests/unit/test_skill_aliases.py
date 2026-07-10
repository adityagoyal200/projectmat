from app.features.matching.skill_aliases import normalize_skill, prereq_match_credit


def test_normalize_alias():
    assert normalize_skill("py") == "python"
    assert normalize_skill("ML") == "machine learning"


def test_family_match_pytorch_tensorflow():
    credit, tier, matched = prereq_match_credit(["PyTorch"], "TensorFlow")
    assert credit == 0.5
    assert tier == "family"
    assert matched == "PyTorch"


def test_exact_match():
    credit, tier, _ = prereq_match_credit(["Python"], "Python")
    assert credit == 1.0
    assert tier == "exact"
