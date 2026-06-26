from app.features.imports.parsers.workbook_parser import parse_workbook

# Assuming tests are run from the backend directory
FIXTURES_DIR = "tests/fixtures"


def read_fixture(filename: str) -> bytes:
    with open(f"{FIXTURES_DIR}/{filename}", "rb") as f:
        return f.read()


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
    print("Issues:", parsed.issues)
    assert len(error_issues) == 0


def test_parse_missing_sheet():
    content = read_fixture("missing_sheet_workbook.xlsx")
    parsed = parse_workbook(content)

    # Missing "Students Info" and "Mentors-projects"
    error_issues = [i for i in parsed.issues if i.severity == "error"]

    assert any("Missing sheet: 'Students Info'" in i.message for i in error_issues)
    assert any("Missing sheet: 'Mentors-projects'" in i.message for i in error_issues)


def test_parse_bad_columns():
    content = read_fixture("bad_columns_workbook.xlsx")
    parsed = parse_workbook(content)

    # Students Info missing Registration Number
    error_issues = [i for i in parsed.issues if i.severity == "error"]
    print("Bad columns issues:", parsed.issues)
    assert any(
        "missing required column: 'registration number'" in i.message.lower()
        for i in error_issues
    )


def test_parse_empty_sheet():
    content = read_fixture("empty_sheet_workbook.xlsx")
    parsed = parse_workbook(content)

    error_issues = [i for i in parsed.issues if i.severity == "error"]
    print("Empty sheet issues:", parsed.issues)
    assert any("is empty" in i.message for i in error_issues)
