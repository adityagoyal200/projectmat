from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import venv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.config import settings
from app.features.matching.llm_client import generate_chat_completion

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RepositoryEvaluationResult:
    repository_url: str
    repository_name: str | None
    status: str
    score: float
    metrics: dict
    findings: list[dict] = field(default_factory=list)
    execution_log: str | None = None
    github_logic_score: float | None = None
    ai_justification: str | None = None


_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
    ".pytest_cache",
    "__pycache__",
}

_LANGUAGE_SUFFIXES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".ipynb": "notebook",
}

_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][^'\"]{12,}"
    ),
    re.compile(r"(?i)\bAWS_SECRET_ACCESS_KEY\b\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{20,}"),
    re.compile(r"(?i)\bsk-[a-zA-Z0-9]{20,}\b"),
]


def _finding(
    severity: str, code: str, message: str, evidence: str | None = None
) -> dict:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "evidence": evidence,
    }


def _parse_repository_name(repository_url: str, local_path: Path | None = None) -> str:
    parsed = urlparse(repository_url)
    if parsed.netloc:
        path = parsed.path.strip("/")
        parts = path.split("/")
        if len(parts) >= 2:
            repo = parts[1].removesuffix(".git")
            return f"{parts[0]}/{repo}"
        if parts and parts[0]:
            return parts[0].removesuffix(".git")

    if local_path is not None:
        return local_path.name

    return Path(repository_url).name


def _iter_repository_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def _is_test_file(path: Path) -> bool:
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    return (
        "tests" in parts
        or "test" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.js")
        or name.endswith(".test.ts")
        or name.endswith(".spec.js")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.tsx")
    )


def _scan_for_secrets(files: list[Path], root: Path) -> list[dict]:
    findings: list[dict] = []

    if shutil.which("trufflehog"):
        try:
            completed = subprocess.run(
                ["trufflehog", "filesystem", str(root), "--json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if completed.stdout:
                for line in completed.stdout.strip().split("\n"):
                    if line.strip():
                        try:
                            vuln = json.loads(line)
                            findings.append(
                                _finding(
                                    "error",
                                    "trufflehog_secret",
                                    "Leaked credential or token detected by TruffleHog.",
                                    vuln.get("DetectorName", "unknown"),
                                )
                            )
                        except json.JSONDecodeError:
                            pass
                if findings:
                    return findings
        except subprocess.TimeoutExpired:
            findings.append(
                _finding("warning", "trufflehog_timeout", "Trufflehog scan timed out.")
            )
        except Exception:
            pass

    scanned = 0
    for path in files:
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip"}:
            continue
        if path.stat().st_size > 256_000:
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                rel = str(path.relative_to(root))
                findings.append(
                    _finding(
                        "error",
                        "possible_secret",
                        "Possible credential or private key committed to the repo.",
                        rel,
                    )
                )
                break
        if len(findings) >= 10:
            break

    if scanned == 0:
        findings.append(
            _finding(
                "warning",
                "no_text_files_scanned",
                "No text source files were small enough to scan for secrets.",
            )
        )
    return findings


def _run_linters(root: Path) -> tuple[float, list[dict]]:
    findings = []
    pylint_score = 1.0
    eslint_penalty = 0.0

    python_files = list(root.rglob("*.py"))
    if python_files and shutil.which("pylint"):
        try:
            completed = subprocess.run(
                ["pylint", str(root), "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            try:
                lint_results = json.loads(completed.stdout)
                errors = sum(
                    1 for e in lint_results if e.get("type") in ["error", "fatal"]
                )
                warnings = sum(1 for e in lint_results if e.get("type") == "warning")
                if errors > 0:
                    pylint_score -= 0.1 * min(errors, 5)
                if warnings > 0:
                    pylint_score -= 0.05 * min(warnings, 4)
                findings.append(
                    _finding(
                        "info",
                        "pylint",
                        f"Pylint completed with {errors} errors and {warnings} warnings.",
                    )
                )
            except json.JSONDecodeError:
                pass
        except Exception:
            findings.append(
                _finding("warning", "pylint_failed", "Failed to run Pylint.")
            )

    js_files = (
        list(root.rglob("*.js"))
        + list(root.rglob("*.ts"))
        + list(root.rglob("*.jsx"))
        + list(root.rglob("*.tsx"))
    )
    if js_files and shutil.which("npx"):
        try:
            completed = subprocess.run(
                [
                    "npx",
                    "eslint",
                    str(root),
                    "--format=json",
                    "--no-error-on-unmatched-pattern",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            try:
                lint_results = json.loads(completed.stdout)
                errors = sum(r.get("errorCount", 0) for r in lint_results)
                if errors > 0:
                    eslint_penalty = 0.1 * min(errors, 5)
                    findings.append(
                        _finding(
                            "info", "eslint", f"ESLint completed with {errors} errors."
                        )
                    )
            except json.JSONDecodeError:
                pass
        except Exception:
            findings.append(
                _finding("warning", "eslint_failed", "Failed to run ESLint.")
            )

    quality_score = max(0.0, pylint_score - eslint_penalty)
    return quality_score, findings


def _run_tests(root: Path, timeout_seconds: int) -> tuple[str, str, dict, list[dict]]:
    findings = []
    metrics = {"coverage": 0.0, "tests_passed": 0, "tests_failed": 0}

    has_python = list(root.rglob("*.py"))
    if not has_python:
        return "skipped", "No Python code found for pytest.", metrics, findings

    req_file = root / "requirements.txt"
    pyproject = root / "pyproject.toml"

    if not req_file.exists() and not pyproject.exists():
        findings.append(
            _finding(
                "warning",
                "no_dependencies",
                "No requirements.txt or pyproject.toml found.",
            )
        )

    try:
        venv_dir = root / ".test_venv"
        venv.create(venv_dir, with_pip=True)

        if sys.platform == "win32":
            pip_exe = str(venv_dir / "Scripts" / "pip.exe")
            pytest_exe = str(venv_dir / "Scripts" / "pytest.exe")
        else:
            pip_exe = str(venv_dir / "bin" / "pip")
            pytest_exe = str(venv_dir / "bin" / "pytest")

        subprocess.run(
            [pip_exe, "install", "pytest", "pytest-cov"],
            check=False,
            capture_output=True,
            timeout=30,
        )

        if req_file.exists():
            subprocess.run(
                [pip_exe, "install", "-r", str(req_file)],
                check=False,
                capture_output=True,
                timeout=60,
            )

        completed = subprocess.run(
            [pytest_exe, "--cov=.", "--cov-branch", "--cov-report=json"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

        output = (completed.stdout or "") + "\n" + (completed.stderr or "")
        status = "passed" if completed.returncode == 0 else "failed"

        cov_file = root / "coverage.json"
        if cov_file.exists():
            try:
                cov_data = json.loads(cov_file.read_text())
                totals = cov_data.get("totals", {})
                num_branches = totals.get("num_branches", 0)
                covered_branches = totals.get("covered_branches", 0)
                if num_branches > 0:
                    metrics["coverage"] = (covered_branches / num_branches) * 100.0
                else:
                    metrics["coverage"] = totals.get("percent_covered", 0.0)
            except Exception:
                pass

        if status == "failed":
            findings.append(
                _finding("error", "tests_failed", "Pytest ran but did not pass.")
            )

        return status, output.strip()[-4000:], metrics, findings

    except subprocess.TimeoutExpired:
        findings.append(
            _finding(
                "error", "tests_timed_out", "Automated tests exceeded the timeout."
            )
        )
        return "timeout", "Test timeout", metrics, findings
    except Exception as e:
        findings.append(_finding("error", "tests_error", f"Error running tests: {e!s}"))
        return "error", str(e), metrics, findings


async def _evaluate_readme(root: Path) -> tuple[float, list[dict]]:
    findings = []
    readme_path = root / "README.md"
    if not readme_path.exists():
        findings.append(
            _finding("warning", "missing_readme", "Repository has no README file.")
        )
        return 0.0, findings

    readme_content = readme_path.read_text(encoding="utf-8", errors="ignore").strip()
    if len(readme_content) < 50:
        findings.append(
            _finding("warning", "short_readme", "README is too short to be meaningful.")
        )
        return 0.1, findings

    if not settings.LLM_ENABLED:
        return 0.10, findings

    system_prompt = """You are a Documentation Grader. Review the provided README file.
Determine its quality based on the following scale:
- 0.1: The README is purely generic, auto-generated framework boilerplate (e.g., default Create React App, Vite, Next.js, or plain scaffolding text with no custom project info).
- 0.25: The README contains meaningful, custom information written by the student about their specific project.

Output ONLY a JSON object:
{
  "score": <0.1 or 0.25>
}
"""
    try:
        res = await generate_chat_completion(
            f"README CONTENT:\n\n{readme_content[:3000]}",
            system_prompt=system_prompt,
            force=settings.LLM_ENABLED,
        )
        content = res.content.strip()
        content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE)
        content = re.sub(r"```$", "", content, flags=re.IGNORECASE).strip()
        parsed = json.loads(content)
        score = float(parsed.get("score") or 0.10)
        return score, findings
    except Exception:
        findings.append(
            _finding(
                "warning", "readme_eval_failed", "LLM evaluation of README failed."
            )
        )
        return 0.10, findings


async def evaluate_repository_path(
    root: Path,
    *,
    repository_url: str | None = None,
    run_tests: bool = False,
    timeout_seconds: int = 30,
    extracted_requirements: dict | None = None,  # noqa: ARG001
) -> RepositoryEvaluationResult:
    """Evaluate a local repository checkout using deterministic local checks."""
    root = root.resolve()
    repo_url = repository_url or str(root)
    repo_name = _parse_repository_name(repo_url, root)
    logger.info(f"[REPO EVALUATION] Evaluating code repository: '{repo_name}'")

    if not root.exists() or not root.is_dir():
        return RepositoryEvaluationResult(
            repository_url=repo_url,
            repository_name=repo_name,
            status="failed",
            score=0.0,
            metrics={"exists": False},
            findings=[
                _finding(
                    "error",
                    "repository_not_found",
                    "Repository path does not exist or is not a directory.",
                    str(root),
                )
            ],
        )

    files = _iter_repository_files(root)
    language_counts: dict[str, int] = {}
    for path in files:
        language = _LANGUAGE_SUFFIXES.get(path.suffix.lower())
        if language:
            language_counts[language] = language_counts.get(language, 0) + 1

    readme_files = [p for p in files if p.name.lower().startswith("readme")]
    license_files = [p for p in files if p.name.lower().startswith("license")]
    test_files = [p for p in files if _is_test_file(p)]
    dependency_files = [
        p
        for p in files
        if p.name
        in {
            "package.json",
            "package-lock.json",
            "pyproject.toml",
            "requirements.txt",
            "poetry.lock",
            "pnpm-lock.yaml",
            "yarn.lock",
            "Cargo.toml",
            "go.mod",
        }
    ]

    findings: list[dict] = []
    if not test_files:
        findings.append(
            _finding(
                "warning", "missing_tests", "No obvious automated tests were found."
            )
        )
    if not dependency_files:
        findings.append(
            _finding(
                "info",
                "missing_dependency_manifest",
                "No common dependency manifest was found.",
            )
        )
    if not language_counts:
        findings.append(
            _finding(
                "warning", "no_source_files", "No recognizable source files were found."
            )
        )

    findings.extend(_scan_for_secrets(files, root))

    lint_score, lint_findings = _run_linters(root)
    findings.extend(lint_findings)

    test_status = "not_run"
    execution_log = None
    test_metrics = {}
    if run_tests and test_files:
        test_status, execution_log, test_metrics, test_findings = _run_tests(
            root, timeout_seconds
        )
        findings.extend(test_findings)
    elif run_tests and not test_files:
        findings.append(
            _finding(
                "warning",
                "test_command_not_detected",
                "Tests were requested, but no test files detected.",
            )
        )

    readme_score, readme_findings = await _evaluate_readme(root)
    findings.extend(readme_findings)

    metrics: dict[str, Any] = {
        "file_count": len(files),
        "source_file_count": sum(language_counts.values()),
        "language_counts": language_counts,
        "has_readme": bool(readme_files),
        "readme_score": readme_score,
        "has_license": bool(license_files),
        "test_file_count": len(test_files),
        "dependency_manifest_count": len(dependency_files),
        "test_status": test_status,
        "test_metrics": test_metrics,
        "lint_score": lint_score,
        "secret_findings": sum(
            1 for f in findings if f["code"] in ["possible_secret", "trufflehog_secret"]
        ),
    }

    # 1. Documentation (README presence/quality): 0.25 marks
    docs_score = 0.00
    if bool(readme_files):
        # readme_score is already 0.10 or 0.25
        docs_score = readme_score

    # 2. Hygiene & Security (TruffleHog / secrets): 0.75 marks
    security_score = 0.75 if metrics["secret_findings"] == 0 else 0.00

    # 3. Code Quality (Linters): 1.00 marks
    quality_score = lint_score  # _run_linters returns 0.0 to 1.0

    # 4. Testing (pytest sandbox execution & coverage): 1.00 marks
    testing_score = 0.00
    if test_files:
        if test_status in ("passed", "failed"):
            raw_cov = test_metrics.get("coverage", 0.0) / 100.0
            testing_score = round(0.25 + (0.75 * raw_cov), 2)
        else:
            testing_score = 0.25

    raw_github_static_score = (
        docs_score + security_score + quality_score + testing_score
    )
    score = round(raw_github_static_score / 3.0, 4)

    metrics["structure_score"] = quality_score
    metrics["testing_score"] = testing_score
    metrics["hygiene_score"] = security_score
    metrics["documentation_score"] = docs_score
    metrics["raw_github_static_score"] = raw_github_static_score

    score_parts = {
        "documentation": docs_score,
        "security": security_score,
        "code_quality": quality_score,
        "testing": testing_score,
    }
    metrics["score_parts"] = score_parts
    logger.info(
        f"[REPO EVALUATION] Completed evaluation for '{repo_name}'. Score: {score:.4f}"
    )

    status = "completed"
    if any(f["severity"] == "error" for f in findings):
        status = "completed_with_errors"

    return RepositoryEvaluationResult(
        repository_url=repo_url,
        repository_name=repo_name,
        status=status,
        score=score,
        metrics=metrics,
        findings=findings,
        execution_log=execution_log,
        github_logic_score=None,
        ai_justification=None,
    )


async def evaluate_repository_reference(
    repository_url: str,
    *,
    local_path: str | None = None,
    clone_remote: bool = False,
    run_tests: bool = False,
    timeout_seconds: int = 30,
    extracted_requirements: dict | None = None,
) -> RepositoryEvaluationResult:
    """Evaluate a repository URL/path, cloning only when explicitly requested."""
    candidate_path = Path(local_path or repository_url)
    if candidate_path.exists():
        return await evaluate_repository_path(
            candidate_path,
            repository_url=repository_url,
            run_tests=run_tests,
            timeout_seconds=timeout_seconds,
            extracted_requirements=extracted_requirements,
        )

    if clone_remote:
        parsed = urlparse(repository_url)
        repo_name = _parse_repository_name(repository_url)
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", repo_name)

        with tempfile.TemporaryDirectory(
            prefix=f"projectmatchai-repo-{safe_name}-"
        ) as tmp:
            checkout = Path(tmp) / "checkout"

            clone_url = repository_url
            if (
                "github.com" in repository_url.lower()
                and settings.GITHUB_TOKEN.strip()
                and parsed.netloc
            ):
                netloc = f"{settings.GITHUB_TOKEN.strip()}@{parsed.netloc}"
                clone_url = parsed._replace(netloc=netloc).geturl()
            elif (
                "gitlab" in repository_url.lower()
                and settings.GITLAB_TOKEN.strip()
                and parsed.netloc
            ):
                netloc = f"oauth2:{settings.GITLAB_TOKEN.strip()}@{parsed.netloc}"
                clone_url = parsed._replace(netloc=netloc).geturl()

            logger.info(
                f"[REPO EVALUATION] Cloning remote repository: '{repository_url}'"
            )
            try:
                completed = subprocess.run(
                    ["git", "clone", clone_url, str(checkout)],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                logger.error(
                    f"[REPO EVALUATION] Git clone timed out for '{repository_url}'!"
                )
                stdout_str = (
                    exc.stdout.decode("utf-8", errors="ignore")
                    if isinstance(exc.stdout, bytes)
                    else str(exc.stdout or "")
                )
                stderr_str = (
                    exc.stderr.decode("utf-8", errors="ignore")
                    if isinstance(exc.stderr, bytes)
                    else str(exc.stderr or "")
                )
                output = f"{stdout_str}\n{stderr_str}"
                return RepositoryEvaluationResult(
                    repository_url=repository_url,
                    repository_name=repo_name,
                    status="failed",
                    score=0.0,
                    metrics={"clone_status": "timeout"},
                    findings=[
                        _finding(
                            "error",
                            "clone_timed_out",
                            "Repository clone exceeded the timeout.",
                        )
                    ],
                    execution_log=output.strip(),
                )

            if completed.returncode != 0:
                logger.error(
                    f"[REPO EVALUATION] Git clone failed for '{repository_url}'!"
                )
                output = (completed.stdout or "") + "\n" + (completed.stderr or "")
                return RepositoryEvaluationResult(
                    repository_url=repository_url,
                    repository_name=repo_name,
                    status="failed",
                    score=0.0,
                    metrics={"clone_status": "failed"},
                    findings=[
                        _finding(
                            "error",
                            "clone_failed",
                            "Repository could not be cloned.",
                        )
                    ],
                    execution_log=output.strip()[-4000:],
                )

            logger.info(
                f"[REPO EVALUATION] Successfully cloned '{repository_url}' into temp directory. Starting code evaluation..."
            )
            return await evaluate_repository_path(
                checkout,
                repository_url=repository_url,
                run_tests=run_tests,
                timeout_seconds=timeout_seconds,
                extracted_requirements=extracted_requirements,
            )

    parsed = urlparse(repository_url)
    parseable = bool(parsed.scheme and parsed.netloc)
    return RepositoryEvaluationResult(
        repository_url=repository_url,
        repository_name=_parse_repository_name(repository_url),
        status="metadata_only",
        score=0.15 if parseable else 0.0,
        metrics={
            "parseable_url": parseable,
            "clone_remote": False,
            "local_path_provided": local_path is not None,
        },
        findings=[
            _finding(
                "warning",
                "repository_not_checked_out",
                "Repository URL was recorded but not cloned or inspected locally.",
            )
        ],
    )
