import pymupdf
import pytest

from lecnotes import workdir
from lecnotes.render import render_deck


def test_render_writes_a_png_and_txt_per_page(synth, tmp_path):
    pdf = synth(tmp_path / "d.pdf", [{"text": "one"}, {"text": "two"}, {"text": "three"}])
    root = tmp_path / "wd"
    render_deck(pdf, root)
    for n in (1, 2, 3):
        assert workdir.page_png(root, n).exists()
        assert workdir.page_txt(root, n).exists()


def test_txt_holds_the_exact_page_text(synth, tmp_path):
    pdf = synth(tmp_path / "d.pdf", [{"text": "conflict serializable"}])
    root = tmp_path / "wd"
    render_deck(pdf, root)
    assert "conflict serializable" in workdir.page_txt(root, 1).read_text()


def test_png_long_edge_is_1400(synth, tmp_path):
    pdf = synth(tmp_path / "d.pdf", [{"text": "one"}])
    root = tmp_path / "wd"
    render_deck(pdf, root)
    pix = pymupdf.Pixmap(workdir.page_png(root, 1))
    assert max(pix.width, pix.height) == 1400


def test_rows_have_exactly_n_png_txt_chars(synth, tmp_path):
    pdf = synth(tmp_path / "d.pdf", [{"text": "plain"}, {"text": "two"}])
    rows = render_deck(pdf, tmp_path / "wd")
    assert [r["n"] for r in rows] == [1, 2]
    assert rows[0]["png"] == "pages/slide-001.png"
    assert rows[0]["txt"] == "pages/slide-001.txt"
    assert rows[0]["chars"] == len("plain")
    assert set(rows[0].keys()) == {"n", "png", "txt", "chars"}


def test_blank_page_reports_zero_chars(synth, tmp_path):
    rows = render_deck(synth(tmp_path / "d.pdf", [{"blank": True}]), tmp_path / "wd")
    assert rows[0]["chars"] == 0


def test_unopenable_pdf_creates_no_pages_dir(tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf")
    root = tmp_path / "wd"
    with pytest.raises(pymupdf.FileDataError):
        render_deck(broken, root)
    assert not workdir.pages_dir(root).exists()
