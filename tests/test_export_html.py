import base64

from lecnotes.export_html import render_html


def test_local_image_is_embedded_as_data_uri(tmp_path, png):
    data = png(tmp_path / "figures" / "slide-001.png").read_bytes()
    html = render_html("![a node](figures/slide-001.png)\n", tmp_path, "notes")
    assert f'src="data:image/png;base64,{base64.b64encode(data).decode()}"' in html
    assert 'src="figures/' not in html


def test_image_only_paragraph_becomes_figure_with_caption(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("Intro.\n\n![The B+ tree root](f.png)\n", tmp_path, "notes")
    assert "<figure><img" in html
    assert "<figcaption>The B+ tree root</figcaption></figure>" in html
    assert "<p>Intro.</p>" in html


def test_empty_alt_gives_figure_without_caption(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("![](f.png)\n", tmp_path, "notes")
    assert "<figure><img" in html
    assert "<figcaption>" not in html


def test_caption_is_escaped(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("![a < b & c](f.png)\n", tmp_path, "notes")
    assert "<figcaption>a &lt; b &amp; c</figcaption>" in html


def test_inline_image_stays_inline(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("See ![icon](f.png) here.\n", tmp_path, "notes")
    assert "<figure>" not in html
    assert html.count("<p>See <img") == 1


def test_tight_list_image_is_not_a_figure(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("- ![icon](f.png)\n- two\n", tmp_path, "notes")
    assert "<figure>" not in html


def test_tables_render(tmp_path):
    html = render_html("| a | b |\n|---|---|\n| 1 | 2 |\n", tmp_path, "notes")
    assert "<table>" in html and "<td>2</td>" in html


def test_raw_html_is_escaped(tmp_path):
    html = render_html("<script>alert(1)</script>\n", tmp_path, "notes")
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_remote_and_data_images_untouched(tmp_path):
    md = "![r](https://example.com/x.png)\n\n![d](data:image/png;base64,AAAA)\n"
    html = render_html(md, tmp_path, "notes")
    assert 'src="https://example.com/x.png"' in html
    assert 'src="data:image/png;base64,AAAA"' in html


def test_title_from_first_h1(tmp_path):
    html = render_html("## Not this\n\n# B+ *Trees*\n\n# Later\n", tmp_path, "notes")
    assert "<title>B+ Trees</title>" in html


def test_title_falls_back_and_is_escaped(tmp_path):
    assert "<title>lec&lt;1&gt;</title>" in render_html("no heading\n", tmp_path, "lec<1>")


def test_page_shell_is_self_contained(tmp_path):
    html = render_html("# T\n\ntext\n", tmp_path, "notes")
    assert html.startswith("<!doctype html>")
    assert '<meta charset="utf-8">' in html
    assert '<meta name="viewport"' in html
    assert "<style>" in html
    assert "prefers-color-scheme: dark" in html
    assert "@media print" in html
    for forbidden in ("<script", "<link", "@import", "http://", "https://"):
        assert forbidden not in html


def test_jpeg_uses_jpeg_mime(tmp_path, png):
    # The bytes are PNG, but the mime type follows the extension.
    png(tmp_path / "photo.JPG")
    assert 'src="data:image/jpeg;base64,' in render_html("![p](photo.JPG)\n", tmp_path, "n")


def test_title_ignores_h1_inside_a_blockquote(tmp_path):
    html = render_html("> # Quoted\n\n# Real\n", tmp_path, "notes")
    assert "<title>Real</title>" in html


def test_symlinked_image_mime_follows_the_src(tmp_path, png):
    png(tmp_path / "blob.png").rename(tmp_path / "blob.bin")
    (tmp_path / "fig.png").symlink_to(tmp_path / "blob.bin")
    assert 'src="data:image/png;base64,' in render_html("![p](fig.png)\n", tmp_path, "n")


MATH_MD = (
    "# Policy $\\pi$ gradients\n\n"
    "Inline $a<b$ and $$x^2$$ here.\n\n"
    "$$\n\\nabla_\\theta J(\\theta)\n$$\n"
)


def test_inline_math_is_escaped_latex_in_a_span(tmp_path):
    html = render_html(MATH_MD, tmp_path, "n")
    assert '<span class="lecnotes-math">a&lt;b</span>' in html


def test_display_math_uses_a_display_div(tmp_path):
    html = render_html(MATH_MD, tmp_path, "n")
    assert '<span class="lecnotes-math lecnotes-math-display">x^2</span>' in html
    assert '<div class="lecnotes-math lecnotes-math-display">\\nabla_\\theta J(\\theta)</div>' in html


def test_double_dollar_mid_paragraph_stays_inline_html(tmp_path):
    # A <div> here would make the browser auto-close the <p>, orphaning the trailing
    # text and leaving a spurious empty <p></p> behind.
    html = render_html("Inline $$x^2$$ here.\n", tmp_path, "n")
    assert '<p>Inline <span class="lecnotes-math lecnotes-math-display">x^2</span> here.</p>' in html
    assert "<div" not in html


def test_katex_is_inlined_only_with_math(tmp_path):
    from lecnotes.katex import katex_js

    with_math = render_html(MATH_MD, tmp_path, "n")
    assert katex_js() in with_math
    assert "throwOnError: false" in with_math and "trust: false" in with_math

    without = render_html("# Plain\n\ntext\n", tmp_path, "n")
    assert "<script" not in without
    assert "katex" not in without.lower()


def test_math_page_makes_no_external_loads(tmp_path):
    html = render_html(MATH_MD, tmp_path, "n")
    for forbidden in ('src="http', "src='http", 'href="http', "url(http", "url(fonts/", "@import", "<link"):
        assert forbidden not in html


def test_title_and_caption_keep_math_source(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("# The $\\pi$ policy\n\n![cap $\\theta$](f.png)\n", tmp_path, "n")
    assert "<title>The \\pi policy</title>" in html
    assert "<figcaption>cap \\theta</figcaption>" in html


def test_math_in_code_is_code(tmp_path):
    html = render_html("`$x$`\n\n```\n$$y$$\n```\n", tmp_path, "n")
    assert "lecnotes-math" not in html
    assert "<script" not in html


def test_display_math_in_blockquote_has_no_stray_quote_marker(tmp_path):
    html = render_html("> $$\n> \\nabla_\\theta J(\\theta)\n> $$\n", tmp_path, "n")
    assert '<div class="lecnotes-math lecnotes-math-display">\\nabla_\\theta J(\\theta)</div>' in html
    # Scoped to the rendered document body: the vendored KaTeX JS legitimately
    # contains the literal string "&gt;" in its own HTML-escaping table.
    body = html.split("<body>\n", 1)[1].split("<script>", 1)[0]
    assert "&gt;" not in body
