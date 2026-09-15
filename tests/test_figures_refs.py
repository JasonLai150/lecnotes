from lecnotes.figures import find_refs


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
