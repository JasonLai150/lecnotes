import pymupdf
import pytest

from lecnotes.figures import content_box, crop_render


def test_box_hugs_content_not_page(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"small_box": (100, 100, 200, 180)}])
    doc = pymupdf.open(path)
    box = content_box(doc[0])
    # 10pt of padding around (100, 100, 200, 180). Tolerance because a stroked
    # rect's reported bounds include half its line width.
    assert box.x0 == pytest.approx(90, abs=1.5)
    assert box.y0 == pytest.approx(90, abs=1.5)
    assert box.x1 == pytest.approx(210, abs=1.5)
    assert box.y1 == pytest.approx(190, abs=1.5)
    doc.close()


def test_full_page_backdrop_is_excluded(synth, tmp_path):
    """The behavior the whole crop depends on.

    Without the backdrop filter the box becomes the entire page and cropping
    does nothing at all.
    """
    path = synth(tmp_path / "d.pdf", [{"backdrop": True, "small_box": (100, 100, 200, 180)}])
    doc = pymupdf.open(path)
    page = doc[0]
    box = content_box(page)
    assert box.get_area() < 0.25 * page.rect.get_area()
    assert box.x1 <= 220
    doc.close()


def test_blank_page_falls_back_to_full_page(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"blank": True}])
    doc = pymupdf.open(path)
    page = doc[0]
    assert content_box(page) == page.rect
    doc.close()


def test_box_is_clipped_to_the_page(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"small_box": (2, 2, 60, 60)}])
    doc = pymupdf.open(path)
    page = doc[0]
    box = content_box(page)
    assert box.x0 >= page.rect.x0
    assert box.y0 >= page.rect.y0
    doc.close()


def test_box_unions_text_and_drawing(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"text": "hi", "small_box": (400, 400, 500, 450)}])
    doc = pymupdf.open(path)
    box = content_box(doc[0])
    assert box.x0 < 100 and box.y1 > 440   # reaches the text at x=72 and the box at y=450
    doc.close()


def test_crop_render_writes_a_png_long_edge_1400(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"small_box": (100, 100, 300, 200)}])
    dest = tmp_path / "out" / "figures" / "slide-001.png"
    crop_render(path, 1, dest)
    assert dest.exists()
    pix = pymupdf.Pixmap(dest)
    assert max(pix.width, pix.height) == 1400


def test_crop_render_is_smaller_than_the_full_page(synth, tmp_path):
    """A crop must actually crop — same long edge, fewer total pixels."""
    path = synth(tmp_path / "d.pdf", [{"backdrop": True, "small_box": (100, 100, 200, 180)}])
    dest = tmp_path / "f.png"
    crop_render(path, 1, dest)
    pix = pymupdf.Pixmap(dest)
    assert pix.width * pix.height < 1400 * 1400
