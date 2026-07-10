"""Downloadable candidate-project fit report (PDF).

Assembles an LLM "how to work on this project / what to improve" analysis with
the deterministic factor breakdown, renders it to Story-safe HTML, and prints
that to PDF via PyMuPDF's Story engine (a core dependency — no extra libraries).
"""

from __future__ import annotations

import asyncio
import html
import io
import json
import logging

import fitz  # PyMuPDF

from app.features.matching.llm_client import generate_chat_completion

logger = logging.getLogger(__name__)


class ReportRenderError(RuntimeError):
    """Raised when the PDF could not be produced."""


_ANALYSIS_SYSTEM = (
    "You are a technical mentor writing a concise, candid readiness report for a "
    "student who wants to work on a specific project. Be specific and actionable. "
    "Respond with ONLY a JSON object, no prose."
)

# The analysis call is best-effort: a single transient provider failure (429/timeout)
# or an unparseable body used to silently degrade the report to the empty skeleton.
# Retry a bounded number of times before falling back so the common transient case
# still produces a full report, while the endpoint never hard-fails.
_ANALYSIS_MAX_ATTEMPTS = 3
_ANALYSIS_RETRY_BASE_DELAY = (
    1.5  # seconds; grows linearly per retry (patched to 0 in tests)
)


def _analysis_skeleton() -> dict:
    """Deterministic empty analysis used when the LLM cannot produce one."""
    return {
        "fit_summary": (
            "Automated analysis was unavailable; this report shows the "
            "deterministic factor breakdown below."
        ),
        "detailed_assessment": "",
        "strengths": [],
        "gaps": [],
        "improvement_plan": [],
        "learning_roadmap": [],
        "recommended_resources": [],
        "project_approach": [],
        "risks": [],
    }


def _parse_analysis_content(content: str) -> dict:
    """Parse and normalize the LLM analysis JSON.

    Raises ValueError/JSONDecodeError on malformed or content-free responses so the
    caller can treat them as retryable failures.
    """
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("LLM analysis response was not a JSON object.")

    def _as_list(value) -> list[str]:
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    fit_summary = str(data.get("fit_summary", "")).strip()
    if not fit_summary:
        raise ValueError("LLM analysis response missing fit_summary.")

    return {
        "fit_summary": fit_summary,
        "detailed_assessment": str(data.get("detailed_assessment", "")).strip(),
        "strengths": _as_list(data.get("strengths")),
        "gaps": _as_list(data.get("gaps")),
        "improvement_plan": _as_list(data.get("improvement_plan")),
        "learning_roadmap": _as_list(data.get("learning_roadmap")),
        "recommended_resources": _as_list(data.get("recommended_resources")),
        "project_approach": _as_list(data.get("project_approach")),
        "risks": _as_list(data.get("risks")),
    }


async def generate_improvement_analysis(
    *,
    candidate_name: str,
    resume_text: str,
    project_title: str,
    project_abstract: str,
    prerequisites: list[str],
    factor_summary: str,
) -> dict:
    """Ask the LLM for a structured fit/improvement analysis.

    Returns a dict with keys: fit_summary, strengths, gaps, improvement_plan,
    project_approach. Falls back to a deterministic skeleton on any failure so
    report generation never hard-fails on the LLM.
    """
    prompt = (
        f"PROJECT: {project_title}\n"
        f"PROJECT ABSTRACT:\n{project_abstract or 'N/A'}\n\n"
        f"REQUIRED SKILLS: {', '.join(prerequisites) or 'N/A'}\n\n"
        f"COMPUTED FACTOR SCORES (0-100):\n{factor_summary}\n\n"
        f"CANDIDATE: {candidate_name}\n"
        f"RESUME (truncated):\n{(resume_text or '')[:9000]}\n\n"
        "Write a thorough, specific readiness report. Return JSON with exactly "
        "these keys:\n"
        "{\n"
        '  "fit_summary": "2-3 sentence honest headline summary of fit",\n'
        '  "detailed_assessment": "5-8 sentence in-depth assessment: how their '
        "background maps to this project, where they are strong, where they will "
        'struggle, and the overall verdict",\n'
        '  "strengths": ["4-6 concrete strengths grounded in their resume/scores, '
        'each with a short why"],\n'
        '  "gaps": ["4-6 specific missing skills or weak areas for THIS project, '
        'each explaining the impact"],\n'
        '  "improvement_plan": ["5-7 prioritized, concrete, actionable steps"],\n'
        '  "learning_roadmap": ["4-6 phased milestones with rough timeframes, e.g. '
        "'Weeks 1-2: ...'\"],\n"
        '  "recommended_resources": ["4-6 specific topics, tools, docs, or course '
        'types to study"],\n'
        '  "project_approach": ["4-6 steps on how they could realistically start '
        'contributing to THIS project"],\n'
        '  "risks": ["2-4 risks or watch-outs for a mentor taking them on"]\n'
        "}\n"
        "Ground every point in the resume and the factor scores above. Be "
        "specific and candid — avoid generic filler."
    )

    for attempt in range(1, _ANALYSIS_MAX_ATTEMPTS + 1):
        try:
            result = await generate_chat_completion(prompt, _ANALYSIS_SYSTEM)
        except Exception as exc:  # unexpected client-side failure
            logger.warning(
                "report.analysis_attempt_failed attempt=%d/%d error=%s",
                attempt,
                _ANALYSIS_MAX_ATTEMPTS,
                exc,
            )
        else:
            if result.skipped:
                # LLM disabled/unconfigured: retrying cannot help.
                logger.warning("report.analysis_skipped reason=%s", result.skip_reason)
                return _analysis_skeleton()
            if result.error is None and (result.content or "").strip():
                try:
                    return _parse_analysis_content(result.content)
                except Exception as exc:
                    logger.warning(
                        "report.analysis_parse_failed attempt=%d/%d error=%s",
                        attempt,
                        _ANALYSIS_MAX_ATTEMPTS,
                        exc,
                    )
            else:
                logger.warning(
                    "report.analysis_provider_error attempt=%d/%d error=%s",
                    attempt,
                    _ANALYSIS_MAX_ATTEMPTS,
                    result.error,
                )

        if attempt < _ANALYSIS_MAX_ATTEMPTS:
            await asyncio.sleep(_ANALYSIS_RETRY_BASE_DELAY * attempt)

    logger.warning(
        "report.analysis_failed exhausted_attempts=%d", _ANALYSIS_MAX_ATTEMPTS
    )
    return _analysis_skeleton()


def _score_color(pct: float) -> str:
    if pct >= 70:
        return "#059669"
    if pct >= 45:
        return "#d97706"
    return "#dc2626"


def build_report_html(context: dict) -> str:
    """Render the report context into Story-safe printable HTML.

    Uses tables + inline styles only (no flex/float/gradient) so PyMuPDF's Story
    layout engine renders it faithfully.
    """
    e = html.escape

    def bullets(items: list[str]) -> str:
        if not items:
            return '<p style="color:#9ca3af;font-style:italic;margin:4px 0">None identified.</p>'
        lis = "".join(f'<li style="margin:3px 0">{e(str(i))}</li>' for i in items)
        return f'<ul style="margin:4px 0 0 0;padding-left:18px">{lis}</ul>'

    def heading(text: str) -> str:
        return (
            f'<p style="color:#4338ca;font-size:13px;font-weight:bold;'
            f'margin:16px 0 4px">{e(text)}</p>'
        )

    a = context["analysis"]
    final_pct = round(context["final_score"] * 100)
    fc = _score_color(final_pct)

    frows = ""
    for f in context["factors"]:
        pct = round(f["score"] * 100)
        col = _score_color(pct)
        frows += (
            '<tr>'
            f'<td style="padding:5px 8px;font-size:11px;font-weight:bold">{e(f["label"])}'
            f'<div style="font-weight:normal;color:#6b7280;font-size:9px">{e(f["meaning"])}</div></td>'
            f'<td style="padding:5px 8px;text-align:right;font-weight:bold;color:{col}">{pct}%</td>'
            '</tr>'
        )
        detail = f.get("detail") or ""
        if detail:
            frows += (
                f'<tr><td colspan="2" style="padding:0 8px 8px 8px;'
                f'color:#6b7280;font-size:9px">{e(detail)}</td></tr>'
            )

    header = (
        '<table style="width:100%"><tr>'
        '<td style="vertical-align:top">'
        f'<div style="font-size:20px;font-weight:bold;color:#111827">{e(context["candidate_name"])}</div>'
        f'<div style="color:#6b7280;font-size:12px">Fit report for '
        f'<b>{e(context["project_title"])}</b></div>'
        '</td>'
        '<td style="text-align:right;vertical-align:top;width:80px">'
        f'<div style="font-size:28px;font-weight:bold;color:{fc}">{final_pct}</div>'
        '<div style="font-size:8px;color:#6b7280">MATCH</div>'
        '</td></tr></table>'
    )

    def paragraph(text: str) -> str:
        if not text:
            return ""
        return f'<p style="margin:4px 0 0 0;line-height:1.5">{e(text)}</p>'

    detailed = a.get("detailed_assessment", "")
    roadmap = a.get("learning_roadmap", [])
    resources = a.get("recommended_resources", [])
    risks = a.get("risks", [])

    return (
        '<html><body style="font-family:sans-serif;color:#1f2937;font-size:12px">'
        f'{header}'
        f'<div style="background-color:#f5f3ff;border:1px solid #ddd6fe;'
        f'padding:10px;margin-top:10px">{e(a["fit_summary"]) or "—"}</div>'
        + (f'{heading("In-depth assessment")}{paragraph(detailed)}' if detailed else "")
        + f'{heading("Strengths for this project")}{bullets(a["strengths"])}'
        + f"{heading('Gaps & what is missing')}{bullets(a['gaps'])}"
        + f'{heading("How to improve & get ready")}{bullets(a["improvement_plan"])}'
        + (
            f'{heading("Suggested learning roadmap")}{bullets(roadmap)}'
            if roadmap
            else ""
        )
        + (
            f'{heading("Recommended resources & topics")}{bullets(resources)}'
            if resources
            else ""
        )
        + f'{heading("How they could approach this project")}{bullets(a["project_approach"])}'
        + (
            f'{heading("Risks & watch-outs for the mentor")}{bullets(risks)}'
            if risks
            else ""
        )
        + f'{heading("Factor breakdown")}'
        + f'<table style="width:100%;border-collapse:collapse">{frows}</table>'
        + '<p style="margin-top:24px;color:#9ca3af;font-size:9px;text-align:center">'
        + f'Generated by ProjectMatch AI · scoring v{e(str(context.get("scoring_version", "")))}</p>'
        + "</body></html>"
    )


# ── Batch selection report ────────────────────────────────────────────────────
# A whole-batch, deterministic (no-LLM) PDF: each student's top-2 projects by the
# same composite score the Batches tab shows, with a factor breakdown and a plain
# "why", plus a comparison against the mentor-selected students recorded in the
# workbook (the "Selected students" column).

_FACTOR_LABELS: list[tuple[str, str]] = [
    ("embedding_similarity", "Topic match"),
    ("prerequisite_overlap", "Required skills"),
    ("resume_experience", "Relevant experience"),
    ("github_score", "GitHub profile"),
    ("coding_profiles_score", "Coding profiles"),
    ("achievements_score", "Achievements"),
]

_SELECTION_STATUS_LABEL = {
    "top1": ("System's #1 pick", "#059669"),
    "top2": ("In system's top 2", "#059669"),
    "outside": ("Not in system's top 2", "#dc2626"),
    "none": ("No selection recorded in workbook", "#6b7280"),
}


def build_deterministic_why(factors: list[dict]) -> str:
    """Produce a short, plain-language rationale from the factor scores.

    Names the two strongest and the weakest signal so the PDF explains *why*
    a project ranked where it did without needing an LLM call.
    """
    ranked = sorted(factors, key=lambda f: f["score"], reverse=True)
    if not ranked:
        return "No signals available for this pairing."

    def phrase(f: dict) -> str:
        return f"{f['label'].lower()} ({round(f['score'] * 100)}%)"

    strong = [f for f in ranked if f["score"] >= 0.45]
    weak = [f for f in ranked if f["score"] < 0.25]

    if strong:
        lead = "Ranked here mainly on " + " and ".join(phrase(f) for f in strong[:2])
    else:
        lead = "A modest overall match, led by " + phrase(ranked[0])

    if weak:
        return f"{lead}; weaker on " + ", ".join(phrase(f) for f in weak[-2:]) + "."
    return lead + "."


def build_batch_report_html(context: dict) -> str:
    """Render the whole-batch selection report (grouped by project) into Story-safe printable HTML."""
    e = html.escape
    summary = context["summary"]

    # ── Cover / summary ──────────────────────────────────────────────────────
    total_students = summary.get("total_students", 0)
    total_projects = summary.get("total_projects", 0)
    with_sel = summary["with_selection"]

    summary_cells = "".join(
        f'<td style="padding:8px 10px;text-align:center;border:1px solid #e5e7eb">'
        f'<div style="font-size:20px;font-weight:bold;color:{color}">{value}</div>'
        f'<div style="font-size:8px;color:#6b7280">{e(label)}</div></td>'
        for value, label, color in [
            (str(total_projects), "Projects", "#111827"),
            (str(total_students), "Students", "#111827"),
            (str(with_sel), "Workbook selections", "#111827"),
        ]
    )

    parts = [
        '<html><body style="font-family:sans-serif;color:#1f2937;font-size:12px">',
        '<div style="font-size:18px;font-weight:bold;color:#111827">'
        f'Batch #{e(str(context["batch_id"]))} — Project-wise selection & recommendation report</div>',
        '<div style="color:#6b7280;font-size:10px;margin-top:2px">'
        "Workbook-selected candidates compared directly against the system's top recommended candidates (as many as the mentor selected, min 3) for each project.</div>",
        f'<table style="width:100%;border-collapse:collapse;margin-top:10px"><tr>'
        f"{summary_cells}</tr></table>",
    ]

    def section_title(text: str) -> str:
        return (
            '<p style="color:#4338ca;font-size:14px;font-weight:bold;'
            "margin:22px 0 4px;border-bottom:1px solid #e5e7eb;"
            f'padding-bottom:3px">{e(text)}</p>'
        )

    # ── By student: each student's top-2 projects ────────────────────────────
    students = context.get("students") or []
    if students:
        parts.append(section_title("By student — each student's top 2 projects"))
    for s in students:
        status_label, status_color = _SELECTION_STATUS_LABEL[s["selection_status"]]
        selected_titles = (
            ", ".join(
                f"{p['project_title']} ({p['mentor_name']})"
                for p in s["selected_projects"]
            )
            or "—"
        )

        parts.append(
            '<table style="width:100%;margin-top:16px;border-top:2px solid #e5e7eb">'
            '<tr><td style="padding-top:8px;vertical-align:top">'
            f'<span style="font-size:14px;font-weight:bold;color:#111827">{e(s["name"])}</span>'
            f'<span style="color:#6b7280;font-size:11px"> · {e(s["registration_number"])}</span>'
            '</td>'
            '<td style="padding-top:8px;text-align:right;vertical-align:top">'
            f'<span style="font-size:10px;font-weight:bold;color:{status_color}">'
            f'{e(status_label)}</span></td></tr></table>'
        )
        parts.append(
            '<div style="font-size:10px;color:#374151;margin:2px 0 2px">'
            f"<b>Workbook-selected project:</b> {e(selected_titles)}</div>"
        )

        for tp in s["top_projects"]:
            sc = round(tp["score"] * 100)
            col = _score_color(sc)
            marker = (
                ' <span style="color:#059669;font-weight:bold">◆ selected</span>'
                if tp["is_selected"]
                else ""
            )
            frows = "".join(
                f'<td style="padding:2px 6px;font-size:8px;color:#6b7280">'
                f'{e(f["label"])}: <b style="color:{_score_color(round(f["score"] * 100))}">'
                f'{round(f["score"] * 100)}%</b></td>'
                for f in tp["factors"]
            )
            parts.append(
                '<table style="width:100%;border-collapse:collapse;margin-top:6px;'
                'background-color:#f9fafb"><tr>'
                '<td colspan="5" style="padding:5px 8px;vertical-align:top">'
                f'<span style="font-weight:bold;font-size:11px">#{tp["rank"]} '
                f'{e(tp["project_title"])}</span>{marker}'
                f'<div style="color:#6b7280;font-size:9px">{e(tp["mentor_name"])}</div>'
                '</td>'
                '<td colspan="1" style="padding:5px 8px;text-align:right;width:56px;vertical-align:top">'
                f'<span style="font-size:16px;font-weight:bold;color:{col}">{sc}</span>'
                '<div style="font-size:7px;color:#6b7280">SCORE</div></td></tr>'
                f'<tr>{frows}</tr>'
                '<tr><td colspan="6" style="padding:2px 8px 6px;font-size:9px;'
                f'color:#374151;line-height:1.4">{e(tp["why"])}</td></tr></table>'
            )

    # ── By project: workbook selections vs. system recommendations ───────────
    if context.get("projects"):
        parts.append(
            section_title("By project — workbook selections vs. system recommendations")
        )
    for p in context["projects"]:
        selected_names = [
            f"{s['name']} ({s['registration_number']})" for s in p["selected_students"]
        ]
        selected_titles = ", ".join(selected_names) or "None recorded in workbook"

        mentor_info = f"Mentor: {e(p['mentor_name'])}"
        if p.get("mentor_email"):
            mentor_info += f" ({e(p['mentor_email'])})"

        parts.append(
            '<table style="width:100%;margin-top:16px;border-top:2px solid #e5e7eb">'
            '<tr><td style="padding-top:6px;vertical-align:top">'
            f'<div style="font-size:12px;font-weight:bold;color:#111827">{e(p["project_title"])}</div>'
            f'<div style="color:#6b7280;font-size:9px">{mentor_info}</div>'
            '</td></tr></table>'
        )
        parts.append(
            '<div style="font-size:9px;color:#374151;margin:4px 0 2px">'
            f"<b>Workbook Selections:</b> {e(selected_titles)}</div>"
        )
        parts.append(
            '<div style="font-size:9px;font-weight:bold;color:#4338ca;margin-top:4px;margin-bottom:2px">'
            "System's Top Recommendations:</div>"
        )

        if not p.get("recommended_students"):
            parts.append(
                '<div style="font-size:9px;color:#9ca3af;font-style:italic;margin-left:10px">No recommendations computed.</div>'
            )
            continue

        for tp in p["recommended_students"]:
            sc = round(tp["score"] * 100)
            col = _score_color(sc)
            marker = (
                ' <span style="color:#059669;font-weight:bold">◆ workbook selected</span>'
                if tp["is_selected"]
                else ""
            )
            frows = "".join(
                f'<td style="padding:2px 4px;font-size:7px;color:#6b7280">'
                f'{e(f["label"])}: <b style="color:{_score_color(round(f["score"] * 100))}">'
                f'{round(f["score"] * 100)}%</b></td>'
                for f in tp["factors"]
            )
            parts.append(
                '<table style="width:100%;border-collapse:collapse;margin-top:4px;'
                'background-color:#f9fafb;border:1px solid #f3f4f6"><tr>'
                '<td colspan="5" style="padding:4px 6px;vertical-align:top">'
                f'<span style="font-weight:bold;font-size:10px">#{tp["rank"]} '
                f'{e(tp["student_name"])}</span>'
                f'<span style="color:#6b7280;font-size:9px"> · {e(tp["registration_number"])}</span>{marker}'
                '</td>'
                '<td colspan="1" style="padding:4px 6px;text-align:right;width:50px;vertical-align:top">'
                f'<span style="font-size:14px;font-weight:bold;color:{col}">{sc}</span>'
                '<div style="font-size:6px;color:#6b7280">SCORE</div></td></tr>'
                f'<tr>{frows}</tr>'
                '<tr><td colspan="6" style="padding:2px 6px 4px;font-size:9px;'
                f'color:#374151;line-height:1.4"><b>Rationale:</b> {e(tp["why"])}</td></tr></table>'
            )

    parts.append(
        '<p style="margin-top:24px;color:#9ca3af;font-size:9px;text-align:center">'
        f'Generated by ProjectMatch AI · deterministic scoring v'
        f'{e(str(context.get("scoring_version", "")))} · {e(context.get("generated_at", ""))}</p>'
    )
    parts.append("</body></html>")
    return "".join(parts)


# Hard ceiling on report pages. fitz.Story's place() loop never terminates if
# some element can't fit the page rect — and because it spins in C code on a
# worker thread, a runaway render can't be cancelled and would hang the
# process. A full batch report measures ~50 pages; 300 is far beyond any
# legitimate report.
_MAX_PDF_PAGES = 300


def _render_pdf_sync(html_str: str) -> bytes:
    buf = io.BytesIO()
    story = fitz.Story(html=html_str)
    writer = fitz.DocumentWriter(buf)
    mediabox = fitz.paper_rect("A4")
    where = fitz.Rect(
        mediabox.x0 + 40, mediabox.y0 + 40, mediabox.x1 - 40, mediabox.y1 - 40
    )
    more = 1
    pages = 0
    while more:
        pages += 1
        if pages > _MAX_PDF_PAGES:
            writer.close()
            raise ReportRenderError(
                f"PDF exceeded {_MAX_PDF_PAGES} pages; layout likely cannot "
                "fit an element and would loop forever."
            )
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()
    return buf.getvalue()


async def render_html_to_pdf(html_str: str) -> bytes:
    """Print HTML to a PDF byte string via PyMuPDF's Story engine (off-thread)."""
    try:
        return await asyncio.to_thread(_render_pdf_sync, html_str)
    except Exception as exc:
        raise ReportRenderError(f"PDF rendering failed: {exc}") from exc
