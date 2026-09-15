import pytest

from lecnotes.figures import find_malformed, find_refs


def test_finds_a_single_ref():
    assert find_refs("![a tree](figures/slide-008.png)") == [8]


def test_finds_refs_with_empty_alt_text():
    assert find_refs("![](figures/slide-012.png)") == [12]


def test_sorts_and_dedupes():
    md = """
    ![x](figures/slide-012.png)
    ![y](figures/slide-003.png)
    ![z](figures/slide-012.png)
    """
    assert find_refs(md) == [3, 12]


def test_ignores_other_images():
    md = "![logo](assets/logo.png) ![ok](figures/slide-005.png) ![n](figures/slide-5.png)"
    assert find_refs(md) == [5]


def test_ignores_prose_that_merely_mentions_the_path():
    assert find_refs("link figures/slide-008.png like this") == []


def test_empty_document_has_no_refs():
    assert find_refs("") == []


def test_alt_text_with_punctuation_still_matches():
    md = "![B+ tree (fanout 133), annotated](figures/slide-014.png)"
    assert find_refs(md) == [14]


def test_slide_numbers_past_999_are_found():
    assert find_refs("![big deck](figures/slide-1000.png)") == [1000]


def test_over_padded_number_is_not_a_ref():
    # finish writes slide-001.png; a link to slide-0001.png would dangle.
    assert find_refs("![x](figures/slide-0001.png)") == []


@pytest.mark.parametrize(
    "target",
    [
        "pages/slide-002.png",
        "./figures/slide-003.png",
        "figures/slide-5.png",
        'figures/slide-001.png "t"',
        "figures/slide-0001.png",
        "out/figures/slide-004.png",
    ],
)
def test_malformed_slide_links_are_reported(target):
    assert find_malformed(f"![cap]({target})") == [target]


@pytest.mark.parametrize(
    "markdown",
    [
        "![cap](figures/slide-001.png)",
        "![](figures/slide-1000.png)",
        "![logo](assets/logo.png)",
        "prose mentioning pages/slide-002.png without an image",
        "[a plain link](pages/slide-002.png)",
        "",
    ],
)
def test_well_formed_and_unrelated_links_are_not_malformed(markdown):
    assert find_malformed(markdown) == []


def test_malformed_targets_are_in_document_order_and_deduplicated():
    md = """
    ![a](pages/slide-009.png)
    ![ok](figures/slide-002.png)
    ![b](./figures/slide-003.png)
    ![c](pages/slide-009.png)
    """
    assert find_malformed(md) == ["pages/slide-009.png", "./figures/slide-003.png"]
