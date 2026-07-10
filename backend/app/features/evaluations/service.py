from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from typing import cast

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.features.candidates.models import Candidate
from app.features.evaluations.codeforces_client import fetch_codeforces_metrics
from app.features.evaluations.context_extractor import extract_project_requirements
from app.features.evaluations.github_client import fetch_github_user_metrics
from app.features.evaluations.kaggle_client import fetch_kaggle_metrics
from app.features.evaluations.leetcode_client import fetch_leetcode_metrics
from app.features.evaluations.live_app_evaluator import evaluate_live_app
from app.features.evaluations.models import LiveAppEvaluation, RepositoryEvaluation
from app.features.evaluations.repository_evaluator import evaluate_repository_reference
from app.features.evaluations.schemas import (
    AgentScoreSubmissionRequest,
    CandidateEvaluationSummary,
    CandidateProfileSummary,
    LiveAppEvaluationResponse,
    RepositoryEvaluationResponse,
)
from app.features.evaluations.scholar_client import fetch_scholar_metrics
from app.features.imports.models import ImportBatch
from app.features.imports.profile_parser import extract_profiles
from app.features.projects.models import Project

logger = structlog.get_logger()


class EvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _build_agent_prompt(
        self,
        *,
        candidate: Candidate,
        github_links: list[str],
        live_links: list[str],
        requirements: dict,
    ) -> str:
        callback_url = (
            f"{settings.agy_callback_base_url}"
            f"/api/evaluations/candidates/{candidate.id}/agent-scores"
        )
        return json.dumps(
            {
                "candidate_id": candidate.id,
                "candidate_name": candidate.name,
                "registration_number": candidate.registration_number,
                "github_links": github_links,
                "live_links": live_links,
                "requirements": requirements,
                "callback": {
                    "method": "POST",
                    "url": callback_url,
                    "schema": {
                        "github_logic_score": "0.0-1.0",
                        "live_feature_score": "0.0-1.0",
                        "live_stability_score": "0.0-1.0",
                        "live_ui_ux_score": "0.0-1.0",
                        "github_justification": "short grounded explanation",
                        "live_justification": "short grounded explanation",
                    },
                },
                "instruction": (
                    "Evaluate repository logic and the deployed live app. "
                    "Submit the final scores to the callback URL."
                ),
            }
        )

    def _launch_agy_agent(self, prompt: str) -> tuple[bool, str]:
        command = settings.AGY_COMMAND.strip() or "agy"

        # A missing binary under `shell=True` does not raise — the shell starts,
        # fails to find the command, prints "<cmd>: not found" to stderr and
        # exits 127, so Popen reports success. Check for the binary up front so
        # a not-installed agy is reported cleanly (→ AgentUnavailable) instead
        # of leaking a shell error and claiming the agent launched.
        if shutil.which(command) is None:
            msg = f"agy command '{command}' not found on PATH; skipping agent."
            logger.info(f"[AGY INITIALIZATION] {msg}")
            return False, msg

        # Build command string for shell execution
        import shlex

        cmd_str = f'{command} --model "{settings.AGY_MODEL}" --print-timeout {settings.AGY_PRINT_TIMEOUT} --prompt {shlex.quote(prompt)} --dangerously-skip-permissions'

        logger.info("[AGY INITIALIZATION] Launching agy browser/code agent...")
        logger.info(f"Command line: {cmd_str}")

        try:
            subprocess.Popen(
                cmd_str,
                shell=True,
            )
        except OSError as exc:
            logger.error(f"[AGY INITIALIZATION] Failed to launch agy: {exc}")
            return False, f"Failed to launch agy: {exc}"

        return True, "agy launch requested."

    async def _load_candidate(self, candidate_id: int) -> Candidate:
        stmt = (
            select(Candidate)
            .options(
                selectinload(Candidate.documents),
                selectinload(Candidate.repository_evaluations),
                selectinload(Candidate.live_app_evaluations),
            )
            .where(Candidate.id == candidate_id)
        )
        result = await self.db.execute(stmt)
        candidate = result.scalars().first()
        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} was not found.")
        return candidate

    def _summary(self, candidate: Candidate) -> CandidateEvaluationSummary:
        return CandidateEvaluationSummary(
            candidate_id=cast(int, candidate.id),
            registration_number=candidate.registration_number,
            candidate_name=candidate.name,
            evaluation_status=candidate.evaluation_status,
            profile=CandidateProfileSummary(
                github_username=candidate.github_username,
                github_metrics=candidate.github_metrics,
                leetcode_username=candidate.leetcode_username,
                leetcode_metrics=candidate.leetcode_metrics,
                codeforces_username=candidate.codeforces_username,
                codeforces_metrics=candidate.codeforces_metrics,
                kaggle_username=candidate.kaggle_username,
                kaggle_metrics=candidate.kaggle_metrics,
                scholar_id=candidate.scholar_id,
                scholar_metrics=candidate.scholar_metrics,
                achievements=candidate.achievements,
                github_repositories=candidate.github_repositories or [],
                live_project_links=candidate.live_project_links or [],
            ),
            repository_evaluations=[
                RepositoryEvaluationResponse.model_validate(row)
                for row in candidate.repository_evaluations
            ],
            live_app_evaluations=[
                LiveAppEvaluationResponse.model_validate(row)
                for row in candidate.live_app_evaluations
            ],
            updated_at=candidate.updated_at,
        )

    def _apply_resume_profiles(self, candidate: Candidate):
        for doc in candidate.documents:
            if doc.document_type == "resume" and doc.parsed_text:
                profiles = extract_profiles(doc.parsed_text)
                candidate.github_username = (
                    candidate.github_username or profiles.github_username
                )
                candidate.leetcode_username = (
                    candidate.leetcode_username or profiles.leetcode_username
                )
                candidate.codeforces_username = (
                    candidate.codeforces_username or profiles.codeforces_username
                )
                candidate.kaggle_username = (
                    candidate.kaggle_username or profiles.kaggle_username
                )
                candidate.scholar_id = candidate.scholar_id or profiles.scholar_id

                if profiles.github_repositories:
                    current_repos = set(candidate.github_repositories or [])
                    current_repos.update(profiles.github_repositories)
                    candidate.github_repositories = list(current_repos)

                if profiles.live_links:
                    current_lives = set(candidate.live_project_links or [])
                    current_lives.update(profiles.live_links)
                    candidate.live_project_links = list(current_lives)

    async def refresh_candidate(
        self,
        candidate_id: int,
        *,
        fetch_remote_profiles: bool = False,
        evaluate_links: bool = True,
        clone_remote_repositories: bool = False,
        run_repository_tests: bool = False,
    ) -> CandidateEvaluationSummary:
        candidate = await self._load_candidate(candidate_id)

        candidate.evaluation_status = "Processing"
        await self.db.commit()

        self._apply_resume_profiles(candidate)

        if fetch_remote_profiles:
            tasks = []
            if candidate.github_username:
                tasks.append(fetch_github_user_metrics(candidate.github_username))
            else:
                tasks.append(asyncio.sleep(0, {}))

            if candidate.leetcode_username:
                tasks.append(fetch_leetcode_metrics(candidate.leetcode_username))
            else:
                tasks.append(asyncio.sleep(0, {}))

            if candidate.codeforces_username:
                tasks.append(fetch_codeforces_metrics(candidate.codeforces_username))
            else:
                tasks.append(asyncio.sleep(0, {}))

            if candidate.scholar_id:
                tasks.append(fetch_scholar_metrics(candidate.scholar_id))
            else:
                tasks.append(asyncio.sleep(0, {}))

            if candidate.kaggle_username:
                tasks.append(fetch_kaggle_metrics(candidate.kaggle_username))
            else:
                tasks.append(asyncio.sleep(0, {}))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            if len(results) == 5:
                if isinstance(results[0], dict) and "fetch_error" not in results[0]:
                    candidate.github_metrics = results[0]
                    if (
                        not candidate.github_repositories
                        and "repository_urls" in results[0]
                    ):
                        candidate.github_repositories = results[0]["repository_urls"]
                if isinstance(results[1], dict) and "fetch_error" not in results[1]:
                    candidate.leetcode_metrics = results[1]
                if isinstance(results[2], dict) and "fetch_error" not in results[2]:
                    candidate.codeforces_metrics = results[2]
                if isinstance(results[3], dict) and "fetch_error" not in results[3]:
                    candidate.scholar_metrics = results[3]
                if isinstance(results[4], dict) and "fetch_error" not in results[4]:
                    candidate.kaggle_metrics = results[4]

        if evaluate_links:
            # Clear stale evaluations before external agent invokes
            await self.db.execute(
                delete(RepositoryEvaluation).where(
                    RepositoryEvaluation.candidate_id == candidate.id
                )
            )
            await self.db.execute(
                delete(LiveAppEvaluation).where(
                    LiveAppEvaluation.candidate_id == candidate.id
                )
            )
            await self.db.commit()

            proj_stmt = select(Project).where(
                Project.import_batch_id == candidate.import_batch_id
            )
            proj_res = await self.db.execute(proj_stmt)
            projects = proj_res.scalars().all()

            project_requirements = {}
            for p in projects:
                if not p.extracted_requirements:
                    reqs = await extract_project_requirements(
                        p.abstract, p.problem_statement_link
                    )
                    p.extracted_requirements = reqs
                    await self.db.flush()
                else:
                    reqs = p.extracted_requirements
                project_requirements[p.id] = reqs

            merged_requirements = {
                "features": [],
                "technologies": [],
                "prerequisites": [],
            }
            for r in project_requirements.values():
                merged_requirements["features"].extend(r.get("features", []))
                merged_requirements["technologies"].extend(r.get("technologies", []))
                merged_requirements["prerequisites"].extend(r.get("prerequisites", []))

            merged_requirements["features"] = list(set(merged_requirements["features"]))
            merged_requirements["technologies"] = list(
                set(merged_requirements["technologies"])
            )
            merged_requirements["prerequisites"] = list(
                set(merged_requirements["prerequisites"])
            )

            github_links = candidate.github_repositories or []
            live_links = candidate.live_project_links or []

            # 1. Deterministic Checks
            for repository_url in github_links:
                result = await evaluate_repository_reference(
                    repository_url,
                    clone_remote=clone_remote_repositories,
                    run_tests=run_repository_tests,
                    extracted_requirements=merged_requirements,
                )
                row = RepositoryEvaluation(
                    candidate_id=candidate.id,
                    repository_url=result.repository_url,
                    repository_name=result.repository_name,
                    source="resume",
                    status=result.status,
                    score=result.score,
                    metrics=result.metrics,
                    findings=result.findings,
                    execution_log=result.execution_log,
                )
                self.db.add(row)

            for url in live_links:
                row = LiveAppEvaluation(
                    candidate_id=candidate.id,
                    url=url,
                    source="resume",
                    status="evaluating_agent",
                    score=0.0,
                    metrics={"agent_pending": True},
                    findings=[],
                    agent_trace=[],
                )
                self.db.add(row)

            candidate.evaluation_status = "EVALUATING"
            await self.db.commit()

            prompt = self._build_agent_prompt(
                candidate=candidate,
                github_links=github_links,
                live_links=live_links,
                requirements=merged_requirements,
            )
            launched, launch_message = self._launch_agy_agent(prompt)
            logger.info(
                "agy.launch_result",
                candidate_id=candidate.id,
                launched=launched,
                message=launch_message,
            )
            if not launched:
                candidate.evaluation_status = "AgentUnavailable"
                for live_eval in candidate.live_app_evaluations:
                    metrics = dict(live_eval.metrics or {})
                    metrics["agent_pending"] = False
                    metrics["agent_launch_error"] = launch_message
                    live_eval.metrics = metrics
                    live_eval.status = "agent_unavailable"
                for repo_eval in candidate.repository_evaluations:
                    findings = list(repo_eval.findings or [])
                    findings.append(
                        {
                            "severity": "warning",
                            "code": "agy_unavailable",
                            "message": launch_message,
                        }
                    )
                    repo_eval.findings = findings

        await self.db.commit()
        candidate = await self._load_candidate(candidate_id)
        return self._summary(candidate)

    async def evaluate_repository_for_candidate(
        self,
        candidate_id: int,
        *,
        repository_url: str,
        local_path: str | None = None,
        clone_remote: bool = False,
        run_tests: bool = False,
    ) -> RepositoryEvaluationResponse:
        candidate = await self._load_candidate(candidate_id)
        result = await evaluate_repository_reference(
            repository_url,
            local_path=local_path,
            clone_remote=clone_remote,
            run_tests=run_tests,
        )
        row = RepositoryEvaluation(
            candidate_id=cast(int, candidate.id),
            repository_url=result.repository_url,
            repository_name=result.repository_name,
            source="manual" if local_path else "resume",
            status=result.status,
            score=result.score,
            metrics=result.metrics,
            findings=result.findings,
            execution_log=result.execution_log,
            github_logic_score=result.github_logic_score,
            ai_justification=result.ai_justification,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(row)
        return RepositoryEvaluationResponse.model_validate(row)

    async def evaluate_live_app_for_candidate(
        self,
        candidate_id: int,
        *,
        url: str,
    ) -> LiveAppEvaluationResponse:
        candidate = await self._load_candidate(candidate_id)
        result = await evaluate_live_app(url)
        row = LiveAppEvaluation(
            candidate_id=cast(int, candidate.id),
            url=result.url,
            source="manual",
            status=result.status,
            score=result.score,
            http_status=result.http_status,
            latency_ms=result.latency_ms,
            metrics=result.metrics,
            findings=result.findings,
            agent_trace=result.agent_trace,
            screenshot_path=result.screenshot_path,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(row)
        return LiveAppEvaluationResponse.model_validate(row)

    async def submit_agent_scores(
        self, candidate_id: int, request: AgentScoreSubmissionRequest
    ) -> CandidateEvaluationSummary:
        candidate = await self._load_candidate(candidate_id)
        was_completed = candidate.evaluation_status == "Completed"

        # Update Repo logic score
        if candidate.repository_evaluations:
            repo_eval = candidate.repository_evaluations[0]
            repo_eval.github_logic_score = request.github_logic_score
            repo_eval.ai_justification = request.github_justification
            metrics = dict(repo_eval.metrics or {})
            metrics["github_logic_score"] = request.github_logic_score
            metrics["github_justification"] = request.github_justification
            repo_eval.metrics = metrics
            self.db.add(repo_eval)

        # Update Live app score
        if candidate.live_app_evaluations:
            live_eval = candidate.live_app_evaluations[0]
            metrics = dict(live_eval.metrics)
            metrics["agent_pending"] = False
            metrics["live_feature_score"] = request.live_feature_score
            metrics["live_stability_score"] = request.live_stability_score
            metrics["live_ui_ux_score"] = request.live_ui_ux_score
            live_eval.metrics = metrics

            # Recalculate total live app score based on agent subscores
            total_live = 0.0
            if request.live_feature_score is not None:
                total_live += request.live_feature_score * 0.5
            if request.live_stability_score is not None:
                total_live += request.live_stability_score * 0.25
            if request.live_ui_ux_score is not None:
                total_live += request.live_ui_ux_score * 0.25

            live_eval.score = total_live
            live_eval.status = "completed"

            if request.live_justification:
                findings = list(live_eval.findings)
                findings.append(
                    {
                        "severity": "info",
                        "code": "agent_justification",
                        "message": request.live_justification,
                    }
                )
                live_eval.findings = findings

            self.db.add(live_eval)

        candidate.evaluation_status = "Completed"

        if candidate.import_batch_id:
            batch = await self.db.get(ImportBatch, candidate.import_batch_id)
            if batch and not was_completed:
                batch.completed_candidates += 1
                if batch.completed_candidates >= batch.total_candidates:
                    batch.status = "Completed"
                self.db.add(batch)

        await self.db.commit()
        candidate = await self._load_candidate(candidate_id)
        return self._summary(candidate)

    async def get_candidate_summary(
        self, candidate_id: int
    ) -> CandidateEvaluationSummary:
        candidate = await self._load_candidate(candidate_id)
        return self._summary(candidate)

    async def refresh_batch(
        self,
        batch_id: int,
        *,
        fetch_remote_profiles: bool = False,
        evaluate_links: bool = True,
        clone_remote_repositories: bool = False,
        run_repository_tests: bool = False,
    ) -> list[CandidateEvaluationSummary]:
        batch = await self.db.get(ImportBatch, batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        stmt = select(Candidate.id).where(Candidate.import_batch_id == batch_id)
        result = await self.db.execute(stmt)
        candidate_ids = list(result.scalars().all())

        batch.status = "Processing"
        batch.total_candidates = len(candidate_ids)
        batch.completed_candidates = 0
        await self.db.commit()

        sem = asyncio.Semaphore(3)

        async def worker(candidate_id: int):
            async with sem:
                # Check cancellation flag
                b = await self.db.get(ImportBatch, batch_id)
                if b and b.cancellation_flag:
                    logger.info(
                        "Batch cancelled, skipping candidate", candidate_id=candidate_id
                    )
                    c = await self.db.get(Candidate, candidate_id)
                    if c:
                        c.evaluation_status = "Failed"
                        await self.db.commit()
                    return None

                lock_stmt = (
                    select(Candidate)
                    .where(Candidate.id == candidate_id)
                    .with_for_update()
                )
                await self.db.execute(lock_stmt)

                try:
                    return await self.refresh_candidate(
                        candidate_id,
                        fetch_remote_profiles=fetch_remote_profiles,
                        evaluate_links=evaluate_links,
                        clone_remote_repositories=clone_remote_repositories,
                        run_repository_tests=run_repository_tests,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to refresh candidate",
                        error=str(e),
                        candidate_id=candidate_id,
                    )
                    c = await self.db.get(Candidate, candidate_id)
                    if c:
                        c.evaluation_status = "Failed"
                        await self.db.commit()
                    return None

        tasks = [worker(cid) for cid in candidate_ids]
        summaries = await asyncio.gather(*tasks)
        return [s for s in summaries if s is not None]
