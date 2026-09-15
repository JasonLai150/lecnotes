### Task 7: Deck rendering

**Files:**
- Create: `src/lecnotes/render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: `lecnotes.workdir`, `lecnotes.figures.TARGET_LONG_EDGE`
- Produces:
  - `FIGURE_IMAGE_AREA = 40_000`, `FIGURE_DRAWING_COUNT = 12`
  - `has_figure(page: pymupdf.Page) -> bool`
  - `render_deck(pdf_path: Path, root: Path) -> list[dict]` — writes `pages/slide-NNN.png` and `.txt`, returns manifest rows `{"n", "png", "txt", "chars", "figure"}`

- [ ] **Step 1: Write the failing test**

Create `tests/test_render.py`:

```python
import pymupdf

from lecnotes import workdir
from lecnotes.render import has_figure, render_deck


def test_text_only_page_has_no_figure(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"text": "just words"}])
    doc = pymupdf.open(path)
    assert has_figure(doc[0]) is False
    doc.close()


def test_page_with_many_drawings_has_a_figure(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"text": "diagram", "many_lines": 20}])
    doc = pymupdf.open(path)
    assert has_figure(doc[0]) is True
    doc.close()


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


def test_rows_carry_n_paths_chars_and_figure_flag(synth, tmp_path):
    pdf = synth(tmp_path / "d.pdf", [{"text": "plain"}, {"text": "fig", "many_lines": 20}])
    rows = render_deck(pdf, tmp_path / "wd")
    assert [r["n"] for r in rows] == [1, 2]
    assert rows[0]["png"] == "pages/slide-001.png"
    assert rows[0]["txt"] == "pages/slide-001.txt"
    assert rows[0]["chars"] == len("plain")
    assert rows[0]["figure"] is False
    assert rows[1]["figure"] is True


def test_blank_page_reports_zero_chars(synth, tmp_path):
    rows = render_deck(synth(tmp_path / "d.pdf", [{"blank": True}]), tmp_path / "wd")
    assert rows[0]["chars"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.render'`

- [ ] **Step 3: Write minimal implementation**

Create `src/lecnotes/render.py`:

```python
"""PDF to per-slide PNG plus per-slide text."""

from pathlib import Path

import pymupdf

from . import workdir
from .figures import TARGET_LONG_EDGE

FIGURE_IMAGE_AREA = 40_000
FIGURE_DRAWING_COUNT = 12


def has_figure(page: pymupdf.Page) -> bool:
    """Whether this page carries something worth looking at rather than reading.

    A hint telling the agent where to look hard — nothing is withheld based on it.
    """
    big_images = [im for im in page.get_images(full=True) if im[2] * im[3] > FIGURE_IMAGE_AREA]
    return bool(big_images) or len(page.get_drawings()) > FIGURE_DRAWING_COUNT


def render_deck(pdf_path: Path, root: Path) -> list[dict]:
    """Render every page into the workdir; return the manifest rows."""
    workdir.pages_dir(root).mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    try:
        rows = []
        for i, page in enumerate(doc, start=1):
            zoom = TARGET_LONG_EDGE / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            pix.save(workdir.page_png(root, i))

            text = page.get_text().strip()
            workdir.page_txt(root, i).write_text(text, encoding="utf-8")

            rows.append(
                {
                    "n": i,
                    "png": workdir.rel_png(i),
                    "txt": workdir.rel_txt(i),
                    "chars": len(text),
                    "figure": has_figure(page),
                }
            )
        return rows
    finally:
        doc.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_render.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/render.py tests/test_render.py
git commit -m "Add deck rendering to pages and manifest rows"
```

---

