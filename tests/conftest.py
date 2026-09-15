"""PDF fixtures synthesized at test time.

Checking in binary decks would make the assertions unreadable — you could not
tell from a test what the page it depends on actually contains. Building each
page here means every test states its own input.
"""

from pathlib import Path

import pymupdf
import pytest

PAGE_W, PAGE_H = 720, 540  # 4:3, the shape of a lecture slide


def _draw(page, spec):
    if spec.get("blank"):
        return

    if spec.get("backdrop"):
        # Keynote and PowerPoint paint this behind every slide. It is the whole
        # reason content_box needs a backdrop filter.
        page.draw_rect(pymupdf.Rect(0, 0, PAGE_W, PAGE_H), color=None, fill=(1, 1, 1))

    if spec.get("text"):
        page.insert_text((72, 100), spec["text"], fontsize=14)

    if spec.get("drawing"):
        page.draw_rect(pymupdf.Rect(100, 200, 400, 400), color=(0, 0, 0), fill=(0.2, 0.4, 0.9))

    for i in range(spec.get("many_lines", 0)):
        y = 150 + i * 8
        page.draw_line(pymupdf.Point(300, y), pymupdf.Point(380, y), color=(0, 0, 0))

    if spec.get("small_box"):
        page.draw_rect(pymupdf.Rect(*spec["small_box"]), color=(0, 0, 0), fill=(0.9, 0.3, 0.3))


def synth_pdf(path, pages) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for spec in pages:
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        _draw(page, spec)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def synth():
    return synth_pdf


@pytest.fixture
def deck_47(tmp_path):
    """A 47-slide deck, matching the numbers used throughout the spec."""
    specs = [{"text": f"Slide {i}"} for i in range(1, 48)]
    specs[7] = {"text": "Slide 8", "many_lines": 20}  # slide 8 carries a figure
    return synth_pdf(tmp_path / "lec1.pdf", specs)


def make_png(path, width=4, height=3) -> Path:
    """A tiny real PNG, so image tests never need checked-in binaries."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), False)
    pix.clear_with(200)
    pix.save(path)
    return path


@pytest.fixture
def png():
    return make_png
