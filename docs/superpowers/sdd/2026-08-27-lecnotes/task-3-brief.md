### Task 3: Synthesized PDF fixtures

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_conftest.py`

**Interfaces:**
- Consumes: nothing
- Produces: `synth_pdf(path, pages) -> Path`, where `pages` is a list of page-spec dicts. Each spec supports keys:
  - `text: str` — drawn at (72, 100), 14pt
  - `drawing: bool` — draws one large filled rectangle. This is a single drawing, so on its own it does **not** trip the figure heuristic; use `many_lines` for that
  - `many_lines: int` — draws that many short line segments (to push the vector-drawing count over 12)
  - `backdrop: bool` — draws a full-page white rectangle first, as Keynote/PowerPoint exports do
  - `small_box: tuple[float, float, float, float] | None` — draws a filled rectangle at that rect, used as "the actual diagram"
  - `blank: bool` — draws nothing at all

  Also produces the pytest fixture `synth` returning that callable, and `deck_47(tmp_path)` returning a 47-page PDF path.

- [ ] **Step 1: Write the failing test**

Create `tests/test_conftest.py`:

```python
import pymupdf


def test_synth_makes_a_pdf_with_the_right_page_count(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"text": "one"}, {"text": "two"}])
    doc = pymupdf.open(path)
    assert len(doc) == 2
    doc.close()


def test_text_page_has_extractable_text(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"text": "hello slides"}])
    doc = pymupdf.open(path)
    assert "hello slides" in doc[0].get_text()
    doc.close()


def test_blank_page_has_no_text(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"blank": True}])
    doc = pymupdf.open(path)
    assert doc[0].get_text().strip() == ""
    doc.close()


def test_backdrop_page_has_a_near_full_page_drawing(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"backdrop": True, "small_box": (100, 100, 200, 180)}])
    doc = pymupdf.open(path)
    page = doc[0]
    areas = [d["rect"].get_area() / page.rect.get_area() for d in page.get_drawings()]
    assert any(a >= 0.95 for a in areas), "expected a full-page backdrop"
    assert any(a < 0.5 for a in areas), "expected a small diagram too"
    doc.close()


def test_deck_47_has_47_pages(deck_47):
    doc = pymupdf.open(deck_47)
    assert len(doc) == 47
    doc.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_conftest.py -v`
Expected: FAIL with `fixture 'synth' not found`

- [ ] **Step 3: Write minimal implementation**

Create `tests/conftest.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_conftest.py -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_conftest.py
git commit -m "Add synthesized PDF fixtures"
```

---

