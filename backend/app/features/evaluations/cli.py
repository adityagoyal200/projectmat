from __future__ import annotations

import argparse
import asyncio

from app.config import settings
from app.features.evaluations.context_extractor import extract_project_requirements
from app.features.evaluations.live_app_evaluator import evaluate_live_app
from app.features.evaluations.repository_evaluator import evaluate_repository_reference


async def run_cli_evaluation(
    repo_url: str,
    live_url: str | None = None,
    problem_url: str | None = None,
    run_tests: bool = False,
    timeout: int = 45,
):
    print("=" * 60)
    print("      ProjectMatchAI - CLI 4-Agent Evaluation Engine")
    print("=" * 60)

    # Agent 1: Context Extractor
    print("\n[Agent 1] Extracting project requirements...")
    if problem_url:
        print(f"  Fetching problem statement from: {problem_url}")
    else:
        print("  No problem statement link provided. Defaulting to abstract context.")

    requirements = await extract_project_requirements(
        abstract="Standard developer project profile matching repository files.",
        problem_statement_link=problem_url,
    )
    print(f"  Core Features Extracted: {requirements.get('features', [])}")
    print(f"  Required Technologies: {requirements.get('technologies', [])}")

    # Agent 2: GitHub Code Reviewer
    print("\n[Agent 2] Executing repository static & LLM review...")
    print(f"  Cloning and evaluating: {repo_url}")
    repo_result = await evaluate_repository_reference(
        repository_url=repo_url,
        clone_remote=True,
        run_tests=run_tests,
        timeout_seconds=timeout,
        extracted_requirements=requirements,
    )

    print(f"  Clone Status: {repo_result.status}")
    print(f"  Deterministic Structural Score: {repo_result.score:.4f}/1.0")
    print(
        f"  GitHub Logic Review Score: {repo_result.github_logic_score or 0.0:.4f}/1.0"
    )
    print("  AI Justification Highlights:")
    justification = repo_result.ai_justification or "No comments generated."
    for line in justification.split("\n")[:10]:
        print(f"    {line}")
    if len(justification.split("\n")) > 10:
        print("    ...")

    # Agent 3: Live App Tester
    live_result = None
    if live_url:
        print("\n[Agent 3] Invoking Playwright browser scanner on live app...")
        print(f"  Target URL: {live_url}")
        live_result = await evaluate_live_app(live_url, timeout_seconds=timeout)
        print(f"  HTTP Status: {live_result.http_status}")
        print(f"  Latency: {live_result.latency_ms or 0} ms")
        print(f"  Live App Score: {live_result.score:.4f}/1.0")
        if live_result.screenshot_path:
            print(f"  Screenshot Saved to: {live_result.screenshot_path}")
    else:
        print("\n[Agent 3] Live App evaluation skipped: no URL provided.")

    # Agent 4: Aggregator
    print("\n[Agent 4] Aggregating final evaluation...")
    w_github_static = 0.40
    w_github_logic = 0.40
    w_live_app = 0.20

    static_score = repo_result.score
    logic_score = repo_result.github_logic_score or 0.0
    app_score = live_result.score if live_result else 0.0

    final_score = (
        w_github_static * static_score
        + w_github_logic * logic_score
        + w_live_app * app_score
    )

    print("=" * 60)
    print("                    EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Repository Static Score (40%): {static_score:.4f}")
    print(f"  GitHub Logic Score (40%):     {logic_score:.4f}")
    print(f"  Live App UI/UX Score (20%):   {app_score:.4f}")
    print(f"  FINAL COMPOSITE SCORE:         {final_score * 10:.2f} / 10.0")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AGY CLI Repository and Live App Evaluator"
    )
    parser.add_argument(
        "--url", required=True, help="GitHub/GitLab repository URL to clone and review"
    )
    parser.add_argument(
        "--live-url", help="Deployed live project link to test via Playwright"
    )
    parser.add_argument(
        "--problem-url",
        help="Public Google Doc URL containing problem statement/requirements",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Execute automated test suits (pytest, npm test)",
    )
    parser.add_argument(
        "--timeout", type=int, default=45, help="Command timeout in seconds"
    )

    args = parser.parse_args()

    # Enforce settings credentials override for CLI testing if desired
    settings.LLM_ENABLED = settings.llm_is_configured()

    asyncio.run(
        run_cli_evaluation(
            repo_url=args.url,
            live_url=args.live_url,
            problem_url=args.problem_url,
            run_tests=args.run_tests,
            timeout=args.timeout,
        )
    )
