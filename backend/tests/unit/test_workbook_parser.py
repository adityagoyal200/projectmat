from app.features.imports.parsers.workbook_parser import parse_workbook

# Assuming tests are run from the backend directory
FIXTURES_DIR = "tests/fixtures"


def read_fixture(filename: str) -> bytes:
    from pathlib import Path

    return Path(f"{FIXTURES_DIR}/{filename}").read_bytes()


def test_parse_valid_workbook():
    content = read_fixture("valid_workbook.xlsx")
    parsed = parse_workbook(content)

    # All sheets should be parsed successfully
    assert len(parsed.students) == 3
    assert len(parsed.mentors) == 1
    assert len(parsed.mentor_projects) == 1
    assert len(parsed.probable_projects) == 1

    # Check some data
    _, student, _ = parsed.students[0]
    assert student.name == "Alice Smith"
    assert student.registration_number == "REG001"
    assert student.email == "alice@example.com"

    # There should be NO error-level issues
    error_issues = [i for i in parsed.issues if i.severity == "error"]
    assert len(error_issues) == 0


def test_parse_missing_sheet():
    content = read_fixture("missing_sheet_workbook.xlsx")
    parsed = parse_workbook(content)

    # Missing "Students Info" and "Mentors-projects"
    error_issues = [i for i in parsed.issues if i.severity == "error"]

    assert any(
        i.code == "sheet.required_missing" and "Students Info" in i.message
        for i in error_issues
    )
    assert any(
        i.code == "sheet.required_missing" and "Mentors-projects" in i.message
        for i in error_issues
    )


def test_parse_bad_columns():
    content = read_fixture("bad_columns_workbook.xlsx")
    parsed = parse_workbook(content)

    # Students Info missing Registration Number
    error_issues = [i for i in parsed.issues if i.severity == "error"]
    assert any(
        i.code == "sheet.required_column_missing"
        and "registration number" in i.message.lower()
        for i in error_issues
    )


def test_parse_empty_sheet():
    content = read_fixture("empty_sheet_workbook.xlsx")
    parsed = parse_workbook(content)

    error_issues = [i for i in parsed.issues if i.severity == "error"]
    assert any(i.code == "sheet.empty" for i in error_issues)


def test_parse_pro_xlsx():
    from pathlib import Path

    path = Path("../pro.xlsx")
    if path.exists():
        content = path.read_bytes()
        parsed = parse_workbook(content)
        assert (
            parsed.resumes_url
            == "https://drive.google.com/drive/folders/1pPADQHbZsoTAgyJbBTGb5T-sIGhUxXCr?usp=sharing"
        )
        assert len(parsed.students) == 20
        student_names = [s[1].name for s in parsed.students]
        assert "Student's Resume" not in student_names
        assert "All resumes" not in student_names

        quality_warnings = [
            i
            for i in parsed.issues
            if i.code in ("project.abstract_missing", "project.prerequisites_missing")
        ]
        assert quality_warnings
        assert all(i.severity == "warning" for i in quality_warnings)
        assert all(not i.blocking for i in quality_warnings)

        warned_rows = {i.row_number for i in quality_warnings}
        for row_num, row, _ in parsed.mentor_projects:
            if row_num in warned_rows:
                if any(
                    i.code == "project.abstract_missing" and i.row_number == row_num
                    for i in quality_warnings
                ):
                    assert row.abstract is None
                if any(
                    i.code == "project.prerequisites_missing"
                    and i.row_number == row_num
                    for i in quality_warnings
                ):
                    assert row.prerequisites is None
