from lecnotes import mdparse


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
