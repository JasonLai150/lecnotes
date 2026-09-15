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
