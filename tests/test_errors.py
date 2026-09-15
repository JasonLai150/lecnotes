import pytest

from lecnotes.errors import LecnotesError


def test_carries_code_message_and_detail():
    err = LecnotesError("notes_empty", "NOTES.md is still the stub", path="a/NOTES.md")
    assert err.code == "notes_empty"
    assert err.message == "NOTES.md is still the stub"
    assert err.detail == {"path": "a/NOTES.md"}


def test_str_is_the_message():
    assert str(LecnotesError("notes_empty", "boom")) == "boom"


@pytest.mark.parametrize(
    "code,expected",
    [
        ("missing_converter", 2),
        ("conversion_failed", 2),
        ("unsupported_format", 1),
        ("workdir_exists", 1),
        ("not_a_workdir", 1),
        ("notes_empty", 1),
        ("figure_out_of_range", 1),
        ("figure_malformed", 1),
        ("source_not_found", 1),
        ("invalid_pdf", 1),
        ("internal_error", 1),
    ],
)
def test_exit_code_per_error_code(code, expected):
    assert LecnotesError(code, "msg").exit_code == expected


def test_to_dict_carries_the_message_and_merges_detail():
    err = LecnotesError("figure_out_of_range", "bad ref", bad_refs=[{"slide": 91, "max": 47}])
    assert err.to_dict() == {
        "ok": False,
        "error": "figure_out_of_range",
        "message": "bad ref",
        "bad_refs": [{"slide": 91, "max": 47}],
    }
