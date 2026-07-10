"""Unit tests for resolving the mentor-filled "Selected students" column.

Mentors record selections by *name*, not registration number, and the import
splits the column on commas. These tests pin the name→reg resolution (and the
stray-comma repair) that the batch selection report relies on — the join that
was previously broken because it compared names against registration numbers.
"""

from app.features.matching.service import _normalize_name, _resolve_selected_names


def test_normalize_name_collapses_case_and_whitespace():
    assert _normalize_name("  Arnab   Chakraborti ") == "arnab chakraborti"
    assert _normalize_name("ARYAN CHAUHAN") == "aryan chauhan"
    assert _normalize_name(None) == ""


def _name_map() -> dict[str, str]:
    return {
        _normalize_name("Aryan Chauhan"): "MDS202513",
        _normalize_name("Arnab Chakraborti"): "MDS202511",
        _normalize_name("Sambit Rout"): "MDS202520",
    }


def test_resolves_plain_names_to_registration_numbers():
    resolved = _resolve_selected_names(["Aryan Chauhan"], _name_map())
    assert resolved == [("MDS202513", "Aryan Chauhan")]


def test_matches_regardless_of_spacing_and_case():
    resolved = _resolve_selected_names(["  aryan   CHAUHAN "], _name_map())
    assert resolved == [("MDS202513", "  aryan   CHAUHAN ")]


def test_rejoins_name_split_by_a_stray_comma():
    # "Arnab,Chakraborti , Sambit Rout" is imported as three tokens; the first
    # two are one person whose name contained a stray comma.
    tokens = ["Arnab", "Chakraborti", "Sambit Rout"]
    resolved = _resolve_selected_names(tokens, _name_map())
    assert resolved == [
        ("MDS202511", "Arnab Chakraborti"),
        ("MDS202520", "Sambit Rout"),
    ]


def test_unresolved_token_is_kept_for_display_with_no_reg():
    resolved = _resolve_selected_names(["Someone Not In Batch"], _name_map())
    assert resolved == [(None, "Someone Not In Batch")]


def test_direct_match_wins_over_join():
    # Two people who each resolve individually must not be merged.
    resolved = _resolve_selected_names(["Aryan Chauhan", "Sambit Rout"], _name_map())
    assert resolved == [
        ("MDS202513", "Aryan Chauhan"),
        ("MDS202520", "Sambit Rout"),
    ]
