import pytest

from lecnotes.figures import find_malformed, find_refs


def test_finds_a_single_ref():
    assert find_refs("![a tree](figures/slide-008.png)") == [8]


def test_finds_refs_with_empty_alt_text():
    assert find_refs("![](figures/slide-012.png)") == [12]


def test_sorts_and_dedupes():
    # Flush-left: 4-space-indented lines are a CommonMark indented code block,
    # which would make markdown-it correctly (but unhelpfully, for this test)
    # treat the images below as code rather than links.
    md = (
        "![x](figures/slide-012.png)\n"
        "![y](figures/slide-003.png)\n"
        "![z](figures/slide-012.png)\n"
    )
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
        # A link title is valid: markdown-it separates it from src, which still
        # resolves to a real figure file.
        '![t](figures/slide-001.png "title")',
        "",
    ],
)
def test_well_formed_and_unrelated_links_are_not_malformed(markdown):
    assert find_malformed(markdown) == []


def test_bare_filename_mention_in_prose_is_reported():
    # We cannot tell a stray mention apart from link markup that failed to
    # parse (the same failure mode as the unbalanced-bracket case above), so
    # both are reported rather than the mention being silently ignored.
    md = "prose mentioning pages/slide-002.png without an image"
    assert find_malformed(md) == ["pages/slide-002.png"]


def test_plain_link_missing_the_bang_is_reported_regardless_of_directory():
    md = "[a plain link](pages/slide-002.png)"
    assert find_malformed(md) == ["pages/slide-002.png"]


def test_malformed_targets_are_in_document_order_and_deduplicated():
    # Flush-left for the same reason as test_sorts_and_dedupes above.
    md = (
        "![a](pages/slide-009.png)\n"
        "![ok](figures/slide-002.png)\n"
        "![b](./figures/slide-003.png)\n"
        "![c](pages/slide-009.png)\n"
    )
    assert find_malformed(md) == ["pages/slide-009.png", "./figures/slide-003.png"]


def test_bracket_in_caption_still_resolves_as_a_ref():
    # A `]` inside the alt text (e.g. from math notation) used to break the
    # regex match entirely, silently dropping the figure.
    md = "![E_{x~p}[f(x)] estimator](figures/slide-019.png)"
    assert find_refs(md) == [19]
    assert find_malformed(md) == []


def test_unbalanced_bracket_in_caption_is_malformed_not_dropped():
    md = "![maps [0,1) to R](figures/slide-020.png)"
    assert find_refs(md) == []
    malformed = find_malformed(md)
    assert any("slide-020.png" in m for m in malformed)


def test_missing_bang_is_malformed():
    md = "[see](figures/slide-021.png)"
    assert find_malformed(md) == ["figures/slide-021.png"]


def test_code_spans_and_fenced_blocks_are_not_scanned():
    md = "`![x](figures/slide-022.png)`\n\n```\n![x](figures/slide-023.png)\n```\n"
    assert find_refs(md) == []
    assert find_malformed(md) == []


def test_link_title_is_valid():
    md = '![t](figures/slide-001.png "title")'
    assert find_refs(md) == [1]
    assert find_malformed(md) == []


@pytest.mark.parametrize(
    "markdown, bad",
    [
        ("![cap](figures/slide-002.PNG)", "figures/slide-002.PNG"),
        ("![cap](figures/SLIDE-002.png)", "figures/SLIDE-002.png"),
        ("[see](figures/slide-003.Png)", "figures/slide-003.Png"),
        ("prose naming figures/slide-004.PNG here", "figures/slide-004.PNG"),
    ],
)
def test_wrong_case_slide_links_are_malformed_not_refs(markdown, bad):
    # finish writes lowercase slide-NNN.png, so only that spelling resolves.
    assert find_refs(markdown) == []
    assert find_malformed(markdown) == [bad]


def test_figure_links_next_to_math_still_resolve():
    md = "Where $\\theta$ is learned:\n\n![policy $\\pi_\\theta$](figures/slide-004.png)\n"
    assert find_refs(md) == [4]
    assert find_malformed(md) == []


def test_figure_link_after_unclosed_display_math_still_resolves():
    md = "$$\nx = 1\n\n## Heading\n\n![f](figures/slide-003.png)\n\nText.\n\n$$\ny\n$$\n"
    assert find_refs(md) == [3]


def test_figure_link_after_unclosed_double_dollar_sentence_still_resolves():
    md = "$$x = 1$$.\n\n## Heading\n\n![f](figures/slide-003.png)\n\n$$\ny\n$$\n"
    assert find_refs(md) == [3]
