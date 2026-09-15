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
    ],
)
def test_slugify(raw, expected):
    assert slugify(raw) == expected
