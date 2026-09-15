# Task 4 Report: Content Box and Cropped Rendering

## Summary
Implemented `src/lecnotes/figures.py` (`PAD`, `BACKDROP_RATIO`, `TARGET_LONG_EDGE`, `content_box()`, `crop_render()`) and `tests/test_figures_box.py`, per the brief. One pymupdf deviation was found and fixed (see below): `page.get_pixmap()` can round a clip rect's device-space bounds outward by an extra pixel, so `crop_render` now rescales the rendered pixmap onto the exact target long edge when that happens. All 7 new tests pass, and the full 29-test suite passes.

## Implementation Details

### Files Created
- `src/lecnotes/figures.py` — `PAD = 10`, `BACKDROP_RATIO = 0.95`, `TARGET_LONG_EDGE = 1400`, `content_box(page) -> pymupdf.Rect`, `crop_render(pdf_path, slide, dest) -> None`.
- `tests/test_figures_box.py` — the 7 tests specified in the brief, copied verbatim.

`content_box` unions text blocks (`page.get_text("blocks")`), embedded images (`page.get_image_info()`), and vector drawings (`page.get_drawings()`), excluding any single image/drawing rect whose area is `>= BACKDROP_RATIO * page_area` (the full-page backdrop rect that slide exporters paint behind every slide). It pads the union by `PAD` points, clips to `page.rect`, and falls back to the full page rect when nothing survives (blank page).

`crop_render` opens the PDF, computes `content_box` for the 1-indexed slide, picks a zoom so the box's long edge maps to `TARGET_LONG_EDGE`, creates `dest`'s parent directories, and writes the cropped render as a PNG.

## TDD Evidence

### RED: test fails for the expected reason
```
Command: uv run pytest tests/test_figures_box.py -v
```
```
ImportError while importing test module '.../tests/test_figures_box.py'.
tests/test_figures_box.py:4: in <module>
    from lecnotes.figures import content_box, crop_render
E   ModuleNotFoundError: No module named 'lecnotes.figures'
...
Interrupted: 1 error during collection
```
Expected failure: `src/lecnotes/figures.py` did not exist yet.

### First GREEN attempt (6/7 passed) — deviation found
After pasting the brief's implementation verbatim, `uv run pytest tests/test_figures_box.py -v` gave 6 passed, 1 failed:
```
tests/test_figures_box.py::test_crop_render_writes_a_png_long_edge_1400 FAILED

    assert max(pix.width, pix.height) == 1400
E   assert 1401 == 1400
E    +  where 1401 = max(1401, 765)
```
Root cause, isolated interactively: for `small_box=(100,100,300,200)`, `content_box` returns `Rect(90, 90, 310, 210)` (220x120), and `zoom = 1400/220 = 6.363636363636363`, for which `220 * zoom == 1400.0` exactly in float64. But `page.get_pixmap(matrix=Matrix(zoom, zoom), clip=clip)` doesn't just scale width/height — it transforms the clip rect's corners into device space (`Rect(572.727…, 572.727…, 1972.727…, 1336.364…)` here, because the clip's own origin isn't at the page origin) and then rounds outward to an integer `irect` (floor the top-left, ceil the bottom-right): `(572, 572, 1973, 1337)`, i.e. width `1973 - 572 = 1401`. The two independent roundings don't preserve the exact 1400.0 span whenever the transformed origin is non-integral, which it generally is for an off-page-origin clip. This is a case where pymupdf's reported pixmap bounds behave differently from what the brief's straight-line `zoom` calculation assumes (rounding is outward/pixel-snapped, not a plain float scale) — not a difference in the backdrop/union behavior, which matched the brief exactly (verified separately: `pymupdf.Rect() | pymupdf.Rect(10,10,20,20) == Rect(10,10,20,20)`, confirming the empty-Rect union assumption in `content_box` holds as written).

Fix (smallest change preserving the brief's stated intent — "1400px long edge"): after rendering, if `max(pix.width, pix.height) != TARGET_LONG_EDGE`, rescale the pixmap with `pymupdf.Pixmap(pix, round(pix.width * fit), round(pix.height * fit))` where `fit = TARGET_LONG_EDGE / long_edge`. Verified this rounding always overshoots (never undershoots) `TARGET_LONG_EDGE`, since floor/ceil only ever widens the pixel span relative to the exact float size — so this is strictly a downscale-to-fit, never an upscale.

### GREEN: tests pass after the fix
```
Command: uv run pytest tests/test_figures_box.py -v
```
```
tests/test_figures_box.py::test_box_hugs_content_not_page PASSED
tests/test_figures_box.py::test_full_page_backdrop_is_excluded PASSED
tests/test_figures_box.py::test_blank_page_falls_back_to_full_page PASSED
tests/test_figures_box.py::test_box_is_clipped_to_the_page PASSED
tests/test_figures_box.py::test_box_unions_text_and_drawing PASSED
tests/test_figures_box.py::test_crop_render_writes_a_png_long_edge_1400 PASSED
tests/test_figures_box.py::test_crop_render_is_smaller_than_the_full_page PASSED
7 passed, 5 warnings in 0.10s
```

### Full suite
```
Command: uv run pytest -v
```
```
29 passed, 5 warnings in 0.13s
```
(22 pre-existing tests from Tasks 1-3, plus the 7 new tests here.)

The 5 warnings are the pre-existing `DeprecationWarning: builtin type SwigPy... has no __module__ attribute` from the `pymupdf` C extension import; unrelated to this change.

## Files Changed
```
src/lecnotes/figures.py    | 66 ++++++++++++++++++++++++++++++++++++++++
tests/test_figures_box.py  | 95 +++++++++++++++++++++++++++++++++++++++++++++++++++++
2 files changed, 161 insertions(+)
```

## Deviations from the brief
One code deviation, described in detail above: `crop_render` rescales the rendered pixmap with `pymupdf.Pixmap(pix, w, h)` when `page.get_pixmap()`'s outward pixel rounding pushes the long edge past `TARGET_LONG_EDGE`. This is additive — the brief's `content_box` and the zoom-selection logic in `crop_render` are otherwise unchanged verbatim. The backdrop-filter and empty-`Rect()`-union behavior the dispatch note flagged as the likely risk area matched the brief's assumptions exactly and needed no change.

## Self-Review
- **Completeness**: `PAD`, `BACKDROP_RATIO`, `TARGET_LONG_EDGE` constants present with brief's values; `content_box` unions text/images/drawings, excludes backdrop-sized elements, pads, clips to page, falls back to full page when empty; `crop_render` is 1-indexed, creates parent dirs, writes a PNG at exactly the 1400px long edge. All 7 brief tests included verbatim and passing.
- **Quality**: Matches the brief's naming and docstrings; the one added block (pixmap rescale) is commented with the specific pymupdf rounding behavior that makes it necessary, not just "fix rounding".
- **Discipline**: No code beyond what the brief specifies plus the minimal rescale fix; no speculative options or parameters added.
- **Testing**: RED confirmed for the right reason (`ModuleNotFoundError`); GREEN confirmed for all 7 new tests individually and the full 29-test suite. No assertions were weakened — `test_crop_render_writes_a_png_long_edge_1400` still asserts `== 1400` exactly, as originally written.
- **Dependency direction**: `src/lecnotes/figures.py` only imports `pathlib` and `pymupdf`, consistent with `global-constraints.md`'s dependency direction (`figures` has no dependents among the tasks built so far and no dependencies beyond `pymupdf`).

## Concerns
None blocking. Flagging for the controller: the pixel-rounding deviation in `crop_render` (see above) is the kind of pymupdf-behavior gap the dispatch note anticipated, just in `crop_render` rather than in `content_box`'s backdrop filter itself. Worth double-checking in review that the rescale approach (rather than, say, adjusting `zoom` upfront) is the fix the controller wants; I judged it simplest and most robust because the outward-rounding offset depends on the clip rect's device-space origin, not just its size, so no single upfront `zoom` correction eliminates it in general.
