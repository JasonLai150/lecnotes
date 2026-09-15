import pytest

from lecnotes.naming import slugify


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("lec1-history", "lec1-history"),
        ("lec8-txn,cc", "lec8-txn-cc"),            # commas appear in real deck names
        ("lec19-gfs,mr", "lec19-gfs-mr"),
        ("Final Review", "final-review"),
        ("CS4440__Lecture  3", "cs4440-lecture-3"),
        ("--leading-and-trailing--", "leading-and-trailing"),
        ("weird!!!name", "weird-name"),
        ("Übung 3", "übung-3"),                    # non-ASCII letters are kept, casefolded
        ("讲义 第一讲", "讲义-第一讲"),
        ("snake_case_deck", "snake-case-deck"),    # underscore is a separator
        ("!!!", "deck"),                           # nothing left: fall back to a name
        ("", "deck"),
    ],
)
def test_slugify(raw, expected):
    assert slugify(raw) == expected
