import io
from typing import Any

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

from app.features.imports.schemas import (
    MentorProjectRow,
    MentorRow,
    ParsedWorkbook,
    ProbableProjectRow,
    StudentRow,
    ValidationIssueOut,
)


def _clean_header(header: str) -> str:
    """Normalize headers by removing whitespace and newlines, and lowercasing."""
    if not isinstance(header, str):
        return ""
    return header.strip().replace("\n", "").replace("\r", "").lower()


# Map canonical header names to their expected variations in the workbook.
HEADER_ALIASES = {
    # Students Info
    "name": ["name"],
    "registration number": ["registration number", "registration_number"],
    "email": ["email", "email id"],
    "phone": ["phone", "phone number"],
    "file": ["file", "resume"],
    # Mentors info
    "mentors": ["mentors", "mentor name"],
    "email id": ["email", "email id"],
    # Mentors-projects
    "short profile of the mentor": ["short profile of the mentor", "mentor profile"],
    "project title": ["project title"],
    "project abstract": ["project abstract"],
    "pre-requisites": ["pre-requisites", "prerequisites"],
    "student's preference - 1": ["student's preference - 1", "student preference 1"],
    "student's preference - 2": ["student's preference - 2", "student preference 2"],
    "student's preference - 3": ["student's preference - 3", "student preference 3"],
    "selected students": [
        "selected students (to be filled by mentors)",
        "selected students",
    ],
    # Probable projects
    "project idea": ["project idea"],
    "author": ["author"],
    "topic": ["topic"],
}

# Define required and optional columns for each sheet.
SHEET_CONFIG = {
    "Students Info": {
        "aliases": ["students info", "students", "students_info"],
        "required": ["name", "registration number"],
        "optional": ["email", "phone", "file"],
    },
    "Mentors info": {
        "aliases": ["mentors info", "mentors", "mentors_info"],
        "required": ["mentors"],
        "optional": ["email id"],
    },
    "Mentors-projects": {
        "aliases": ["mentors-projects", "mentor projects", "mentor_projects"],
        "required": ["mentors", "project title"],
        "optional": [
            "short profile of the mentor",
            "project abstract",
            "pre-requisites",
            "student's preference - 1",
            "student's preference - 2",
            "student's preference - 3",
            "selected students",
        ],
    },
    "Probable projects": {
        "aliases": ["probable projects", "probable_projects"],
        "required": ["project idea"],
        "optional": ["author", "topic"],
    },
}


def _find_sheet(wb: openpyxl.Workbook, sheet_name: str) -> Worksheet | None:
    """Find a sheet in the workbook using its aliases."""
    config = SHEET_CONFIG[sheet_name]
    for ws_name in wb.sheetnames:
        if _clean_header(ws_name) in config["aliases"]:
            return wb[ws_name]
    return None


def _map_headers(
    ws: Worksheet, sheet_name: str, issues: list[ValidationIssueOut]
) -> dict[str, int] | None:
    """Map canonical column names to their 0-indexed position in the worksheet."""
    is_empty = False
    if ws.max_row < 1 or ws.max_row == 1 and all(cell.value is None for cell in ws[1]):
        is_empty = True

    if is_empty:
        issues.append(
            ValidationIssueOut(
                sheet_name=sheet_name,
                severity="error",
                message=f"Sheet '{sheet_name}' is empty.",
            )
        )
        return None

    headers: list[str] = [str(cell.value) if cell.value else "" for cell in ws[1]]
    cleaned_headers = [_clean_header(h) for h in headers]

    col_map = {}
    config = SHEET_CONFIG[sheet_name]
    all_expected = config["required"] + config["optional"]

    for expected in all_expected:
        aliases = HEADER_ALIASES.get(expected, [expected])
        found = False
        for idx, header in enumerate(cleaned_headers):
            if header in aliases:
                col_map[expected] = idx
                found = True
                break

        if not found and expected in config["required"]:
            issues.append(
                ValidationIssueOut(
                    sheet_name=sheet_name,
                    row_number=1,
                    severity="error",
                    message=f"Missing required column: '{expected}'.",
                )
            )

    # Return None if we are missing any required columns.
    for req in config["required"]:
        if req not in col_map:
            return None

    return col_map


def _get_val(
    row: tuple[Any, ...], col_map: dict[str, int], col_name: str
) -> str | None:
    idx = col_map.get(col_name)
    if idx is None or idx >= len(row):
        return None
    val = row[idx].value
    if val is None:
        return None
    return str(val).strip()


def _is_empty_row(row: tuple[Any, ...]) -> bool:
    return all(cell.value is None or str(cell.value).strip() == "" for cell in row)


def _validate_email(email: str | None) -> bool:
    if not email:
        return True
    if "@" not in email or email.strip().lower() in ["n/a", "na", "-"]:
        return False
    return True


def parse_workbook(file_content: bytes) -> ParsedWorkbook:
    """Parse the workbook and extract all typed rows and validation issues."""
    parsed = ParsedWorkbook()
    issues = parsed.issues

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
    except Exception as e:
        issues.append(
            ValidationIssueOut(
                severity="error",
                message=f"Failed to open workbook: {e!s}",
            )
        )
        return parsed

    # 1. Students Info
    ws_students = _find_sheet(wb, "Students Info")
    if not ws_students:
        issues.append(
            ValidationIssueOut(
                severity="error", message="Missing sheet: 'Students Info'"
            )
        )
    else:
        col_map = _map_headers(ws_students, "Students Info", issues)
        if col_map:
            seen_regs = set()
            for r_idx, row in enumerate(ws_students.iter_rows(min_row=2), start=2):
                if _is_empty_row(row):
                    continue

                name = _get_val(row, col_map, "name")
                reg = _get_val(row, col_map, "registration number")
                email = _get_val(row, col_map, "email")
                phone = _get_val(row, col_map, "phone")
                file = _get_val(row, col_map, "file")

                raw_data = {
                    "name": name,
                    "registration_number": reg,
                    "email": email,
                    "phone": phone,
                    "file": file,
                }

                if not name:
                    issues.append(
                        ValidationIssueOut(
                            sheet_name="Students Info",
                            row_number=r_idx,
                            column_name="Name",
                            severity="error",
                            message="Student name is missing.",
                        )
                    )
                if not reg:
                    issues.append(
                        ValidationIssueOut(
                            sheet_name="Students Info",
                            row_number=r_idx,
                            column_name="Registration Number",
                            severity="error",
                            message="Registration number is missing.",
                        )
                    )
                elif reg in seen_regs:
                    issues.append(
                        ValidationIssueOut(
                            sheet_name="Students Info",
                            row_number=r_idx,
                            column_name="Registration Number",
                            severity="error",
                            message=f"Duplicate registration number: {reg}",
                        )
                    )
                else:
                    seen_regs.add(reg)

                if email and not _validate_email(email):
                    issues.append(
                        ValidationIssueOut(
                            sheet_name="Students Info",
                            row_number=r_idx,
                            column_name="Email",
                            severity="warning",
                            message=f"Invalid email format: {email}",
                        )
                    )

                if not file:
                    issues.append(
                        ValidationIssueOut(
                            sheet_name="Students Info",
                            row_number=r_idx,
                            column_name="File",
                            severity="warning",
                            message="Resume file is missing.",
                        )
                    )

                parsed.students.append((r_idx, StudentRow(**raw_data), raw_data))

    # 2. Mentors info
    ws_mentors = _find_sheet(wb, "Mentors info")
    if not ws_mentors:
        issues.append(
            ValidationIssueOut(
                severity="error", message="Missing sheet: 'Mentors info'"
            )
        )
    else:
        col_map = _map_headers(ws_mentors, "Mentors info", issues)
        if col_map:
            for r_idx, row in enumerate(ws_mentors.iter_rows(min_row=2), start=2):
                if _is_empty_row(row):
                    continue

                name = _get_val(row, col_map, "mentors")
                email = _get_val(row, col_map, "email id")

                raw_data = {"name": name, "email": email}

                if not name:
                    issues.append(
                        ValidationIssueOut(
                            sheet_name="Mentors info",
                            row_number=r_idx,
                            column_name="Mentors",
                            severity="error",
                            message="Mentor name is missing.",
                        )
                    )
                if email and not _validate_email(email):
                    issues.append(
                        ValidationIssueOut(
                            sheet_name="Mentors info",
                            row_number=r_idx,
                            column_name="email id",
                            severity="warning",
                            message=f"Invalid email format: {email}",
                        )
                    )

                parsed.mentors.append((r_idx, MentorRow(**raw_data), raw_data))

    # 3. Mentors-projects
    ws_projects = _find_sheet(wb, "Mentors-projects")
    if not ws_projects:
        issues.append(
            ValidationIssueOut(
                severity="error", message="Missing sheet: 'Mentors-projects'"
            )
        )
    else:
        col_map = _map_headers(ws_projects, "Mentors-projects", issues)
        if col_map:
            for r_idx, row in enumerate(ws_projects.iter_rows(min_row=2), start=2):
                if _is_empty_row(row):
                    continue

                mentor = _get_val(row, col_map, "mentors")
                profile = _get_val(row, col_map, "short profile of the mentor")
                title = _get_val(row, col_map, "project title")
                abstract = _get_val(row, col_map, "project abstract")
                prereqs = _get_val(row, col_map, "pre-requisites")
                pref1 = _get_val(row, col_map, "student's preference - 1")
                pref2 = _get_val(row, col_map, "student's preference - 2")
                pref3 = _get_val(row, col_map, "student's preference - 3")
                selected = _get_val(row, col_map, "selected students")

                raw_data = {
                    "mentor_name": mentor,
                    "mentor_profile": profile,
                    "title": title,
                    "abstract": abstract,
                    "prerequisites": prereqs,
                    "preference_1": pref1,
                    "preference_2": pref2,
                    "preference_3": pref3,
                    "selected_students": selected,
                }

                if not mentor:
                    issues.append(
                        ValidationIssueOut(
                            sheet_name="Mentors-projects",
                            row_number=r_idx,
                            column_name="Mentors",
                            severity="error",
                            message="Mentor name is missing.",
                        )
                    )
                if not title:
                    issues.append(
                        ValidationIssueOut(
                            sheet_name="Mentors-projects",
                            row_number=r_idx,
                            column_name="Project Title",
                            severity="error",
                            message="Project title is missing.",
                        )
                    )

                parsed.mentor_projects.append(
                    (r_idx, MentorProjectRow(**raw_data), raw_data)
                )

    # 4. Probable projects
    ws_probable = _find_sheet(wb, "Probable projects")
    if not ws_probable:
        # Optional sheet, but we log a warning if we want to be strict. The spec doesn't require it to fail.
        pass
    else:
        col_map = _map_headers(ws_probable, "Probable projects", issues)
        if col_map:
            for r_idx, row in enumerate(ws_probable.iter_rows(min_row=2), start=2):
                if _is_empty_row(row):
                    continue

                idea = _get_val(row, col_map, "project idea")
                author = _get_val(row, col_map, "author")
                topic = _get_val(row, col_map, "topic")

                raw_data = {"idea": idea, "author": author, "topic": topic}

                if not idea:
                    issues.append(
                        ValidationIssueOut(
                            sheet_name="Probable projects",
                            row_number=r_idx,
                            column_name="Project Idea",
                            severity="warning",
                            message="Project idea is missing.",
                        )
                    )

                parsed.probable_projects.append(
                    (r_idx, ProbableProjectRow(**raw_data), raw_data)
                )

    return parsed
