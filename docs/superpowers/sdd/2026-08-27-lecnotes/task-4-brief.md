### Task 4: Content box and cropped rendering

**Files:**
- Create: `src/lecnotes/figures.py`
- Create: `tests/test_figures_box.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `PAD = 10`, `BACKDROP_RATIO = 0.95`, `TARGET_LONG_EDGE = 1400`
  - `content_box(page: pymupdf.Page) -> pymupdf.Rect`
  - `crop_render(pdf_path: Path, slide: int, dest: Path) -> None` — 1-indexed slide, writes a PNG cropped to the content box at 1400px long edge, creating parent dirs

- [ ] **Step 1: Write the failing test**

Create `tests/test_figures_box.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_figures_box.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.figures'`

- [ ] **Step 3: Write minimal implementation**

Create `src/lecnotes/figures.py`:

```python
"""Content-box detection and cropped figure rendering."""

from pathlib import Path

import pymupdf

PAD = 10  # points of breathing room around the content box
BACKDROP_RATIO = 0.95
TARGET_LONG_EDGE = 1400


def content_box(page: pymupdf.Page) -> pymupdf.Rect:
    """Union of everything drawn on the page, clipped to the page itself.

    Slide exports paint a full-page white rectangle behind every slide. Counting
    it would make the content box the whole page and defeat the crop, so anything
    covering nearly the entire page is treated as backdrop rather than content.
    """
    page_area = page.rect.get_area()

    def backdrop(rect: pymupdf.Rect) -> bool:
        return rect.get_area() >= BACKDROP_RATIO * page_area

    box = pymupdf.Rect()
    for block in page.get_text("blocks"):
        box |= pymupdf.Rect(block[:4])
    for img in page.get_image_info():
        rect = pymupdf.Rect(img["bbox"])
        if not backdrop(rect):
            box |= rect
    for drawing in page.get_drawings():
        if not backdrop(drawing["rect"]):
            box |= drawing["rect"]

    if box.is_empty:
        return page.rect
    box += (-PAD, -PAD, PAD, PAD)
    return box & page.rect


def crop_render(pdf_path: Path, slide: int, dest: Path) -> None:
    """Render one 1-indexed slide, cropped to its content box, to `dest`.

    Re-rendering from the PDF rather than cropping the page PNG means the crop
    gets the full 1400px long edge to itself, which is what makes small diagram
    labels legible.
    """
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[slide - 1]
        clip = content_box(page)
        zoom = TARGET_LONG_EDGE / max(clip.width, clip.height)
        dest.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip).save(dest)
    finally:
        doc.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_figures_box.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/figures.py tests/test_figures_box.py
git commit -m "Add content-box detection and cropped figure rendering"
```

---

