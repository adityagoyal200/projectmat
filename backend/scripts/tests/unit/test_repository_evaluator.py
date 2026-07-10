import pytest

from app.features.evaluations.repository_evaluator import (
    evaluate_repository_path,
    evaluate_repository_reference,
)


@pytest.mark.anyio
async def test_repository_evaluator_scores_local_project(tmp_path):
    (tmp_path / "README.md").write_text("# Demo\n\nUseful project.", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'", encoding="utf-8")
    (tmp_path / "app.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text(
        "from app import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )

    result = await evaluate_repository_path(tmp_path)

    assert result.status == "completed"
    assert result.score >= 0.7
    assert result.metrics["has_readme"] is True
    assert result.metrics["test_file_count"] == 1
    assert not any(f["code"] == "possible_secret" for f in result.findings)


@pytest.mark.anyio
async def test_repository_evaluator_detects_secret(tmp_path):
    (tmp_path / "app.py").write_text(
        'API_KEY = "abcdefghijklmnopqrstuvwxyz"\n',
        encoding="utf-8",
    )

    result = await evaluate_repository_path(tmp_path)

    assert result.status == "completed_with_errors"
    assert any(f["code"] == "possible_secret" for f in result.findings)


@pytest.mark.anyio
async def test_repository_reference_records_metadata_without_clone():
    result = await evaluate_repository_reference("https://github.com/example/project")

    assert result.status == "metadata_only"
    assert result.repository_name == "example/project"
    assert result.metrics["parseable_url"] is True
    assert result.findings[0]["code"] == "repository_not_checked_out"
