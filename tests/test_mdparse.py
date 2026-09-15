from lecnotes import mdparse
from lecnotes.mdparse import PARSER, inline_text


def _inline_types(md):
    return [(t.type, t.content) for t in mdparse.inline_tokens(md)]


def test_new_parser_returns_independent_instances():
    assert mdparse.new_parser() is not mdparse.new_parser()


def test_parser_renders_tables_and_strikethrough():
    md = "| a | b |\n|---|---|\n| 1 | 2 |\n\n~~gone~~\n"
    html = mdparse.PARSER.render(md)
    assert "<table>" in html
    assert "<s>gone</s>" in html


def test_parser_escapes_raw_html():
    html = mdparse.PARSER.render("<script>alert(1)</script>\n")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_inline_tokens_yields_images_in_order():
    md = "![a](one.png) text ![b](two.png)\n\n| x |\n|---|\n| ![c](three.png) |\n"
    srcs = [t.attrGet("src") for t in mdparse.inline_tokens(md) if t.type == "image"]
    assert srcs == ["one.png", "two.png", "three.png"]


def test_inline_tokens_never_yields_code():
    md = "`![a](one.png)`\n\n```\n![b](two.png)\n```\n\n    ![c](three.png)\n"
    types = {t.type for t in mdparse.inline_tokens(md)}
    assert "image" not in types


def test_inline_and_double_inline_math():
    kinds = _inline_types(r"Policy $\pi_\theta$ and $$x^2$$ here." + "\n")
    assert ("math_inline", r"\pi_\theta") in kinds
    assert ("math_inline_double", "x^2") in kinds


def test_display_math_block():
    blocks = [t for t in PARSER.parse("Text.\n\n$$\n\\sum_t r_t\n$$\n") if t.type == "math_block"]
    assert len(blocks) == 1
    assert blocks[0].content.strip() == r"\sum_t r_t"


def test_emphasis_characters_stay_inside_math():
    kinds = _inline_types("$a_i * b_j * c$\n")
    assert kinds == [("math_inline", "a_i * b_j * c")]


def test_prices_spaces_and_code_are_not_math():
    # Separate paragraphs, so one case's dollar can't pair with another's.
    kinds = _inline_types("Costs $5 and $6.\n\nAlso $ x $ here.\n\n`$code$`\n")
    assert not any(t.startswith("math") for t, _ in kinds)


def test_unclosed_display_math_does_not_swallow_the_document():
    tokens = PARSER.parse("$$\nunclosed\n\nnext para\n")
    assert not any(t.type == "math_block" for t in tokens)
    assert any(t.type == "inline" and t.content == "next para" for t in tokens)


def test_inline_text_keeps_math_source():
    heading = PARSER.parse("# The $\\pi$ *policy*\n")[1]
    assert inline_text(heading.children) == r"The \pi policy"


def test_inline_text_of_image_alt_keeps_math():
    inline = PARSER.parse("![cap $\\theta$ `x`](f.png)\n")[1]
    assert inline_text(inline.children) == r"cap \theta x"


def test_indented_display_math_is_a_code_block_not_math():
    tokens = PARSER.parse("Text.\n\n    $$\n    x^2\n    $$\n")
    assert not any(t.type == "math_block" for t in tokens)
    assert any(t.type == "code_block" for t in tokens)


def test_display_math_in_blockquote_strips_the_quote_marker():
    md = "> text\n>\n> $$\n> \\nabla_\\theta J(\\theta)\n> $$\n"
    blocks = [t for t in PARSER.parse(md) if t.type == "math_block"]
    assert len(blocks) == 1
    assert blocks[0].content.strip() == r"\nabla_\theta J(\theta)"
    assert not any(line.startswith(">") for line in blocks[0].content.splitlines())


def test_display_math_in_nested_blockquote_strips_both_markers():
    blocks = [t for t in PARSER.parse("> > $$\n> > x^2\n> > $$\n") if t.type == "math_block"]
    assert len(blocks) == 1
    assert blocks[0].content.strip() == "x^2"
    assert not any(line.startswith(">") for line in blocks[0].content.splitlines())


def test_display_math_gt_inside_the_latex_is_kept():
    # Only the leading blockquote markers are stripped, not a ">" the LaTeX itself uses.
    blocks = [t for t in PARSER.parse("> $$\n> a > b\n> $$\n") if t.type == "math_block"]
    assert len(blocks) == 1
    assert blocks[0].content.strip() == "a > b"


def test_top_level_display_math_is_unaffected_by_the_blockquote_fix():
    blocks = [t for t in PARSER.parse("$$\n\\sum_t r_t\n$$\n") if t.type == "math_block"]
    assert len(blocks) == 1
    assert blocks[0].content.strip() == r"\sum_t r_t"


def test_unclosed_display_math_swallows_at_most_one_paragraph():
    md = "$$\nx = 1\n\n## Heading\n\n![f](figures/slide-003.png)\n\nText.\n\n$$\ny\n$$\n"
    tokens = PARSER.parse(md)
    assert any(t.type == "heading_open" for t in tokens)
    math_blocks = [t for t in tokens if t.type == "math_block"]
    assert len(math_blocks) == 1
    assert math_blocks[0].content.strip() == "y"


def test_unclosed_double_dollar_sentence_swallows_at_most_one_paragraph():
    md = "$$x = 1$$.\n\n## Heading\n\n![f](figures/slide-003.png)\n\n$$\ny\n$$\n"
    tokens = PARSER.parse(md)
    assert any(t.type == "heading_open" for t in tokens)
    math_blocks = [t for t in tokens if t.type == "math_block"]
    assert len(math_blocks) == 1
    assert math_blocks[0].content.strip() == "y"


def test_display_math_inside_a_list_item_is_indented_to_the_item_text():
    md = "1. Item text\n\n   $$\n   x^2\n   $$\n\n2. Next\n"
    tokens = PARSER.parse(md)
    assert any(t.type == "math_block" for t in tokens)
    assert sum(1 for t in tokens if t.type == "ordered_list_open") == 1
