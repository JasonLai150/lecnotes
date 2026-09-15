# Task 7 report: Deck rendering

## What I implemented

`src/lecnotes/render.py`:
- `FIGURE_IMAGE_AREA = 40_000`, `FIGURE_DRAWING_COUNT = 12` constants.
- `has_figure(page) -> bool`: true if the page has an embedded image with area > 40,000, or more than 12 vector drawings.
- `render_deck(pdf_path, root) -> list[dict]`: opens the PDF, renders each page to `pages/slide-NNN.png` at the 1400px long edge (via `figures.TARGET_LONG_EDGE`), writes the stripped page text to `pages/slide-NNN.txt`, and returns one manifest row per page: `{"n", "png", "txt", "chars", "figure"}`, using `workdir.page_png/page_txt/rel_png/rel_txt`.

Implementation matches the brief's Step 3 code verbatim, with one change: I did **not** add the pymupdf off-by-one rescale fix from `figures.crop_render` (see Deviations below).

`tests/test_render.py`: the 7 tests exactly as specified in the brief.

## TDD evidence

**RED**

Command: `uv run pytest tests/test_render.py -v`

Relevant output:
```
ImportError while importing test module '.../tests/test_render.py'.
tests/test_render.py:4: in <module>
    from lecnotes.render import has_figure, render_deck
E   ModuleNotFoundError: No module named 'lecnotes.render'
```
Expected reason: `src/lecnotes/render.py` did not exist yet — matches the brief's expected failure exactly.

**GREEN**

Command: `uv run pytest tests/test_render.py -v`

Output:
```
tests/test_render.py::test_text_only_page_has_no_figure PASSED
tests/test_render.py::test_page_with_many_drawings_has_a_figure PASSED
tests/test_render.py::test_render_writes_a_png_and_txt_per_page PASSED
tests/test_render.py::test_txt_holds_the_exact_page_text PASSED
tests/test_render.py::test_png_long_edge_is_1400 PASSED
tests/test_render.py::test_rows_carry_n_paths_chars_and_figure_flag PASSED
tests/test_render.py::test_blank_page_reports_zero_chars PASSED

7 passed, 5 warnings in 0.25s
```

Full suite: `uv run pytest -q` → `50 passed, 5 warnings in 0.31s` (43 existing + 7 new, as expected).

## Files changed

- `src/lecnotes/render.py` (new)
- `tests/test_render.py` (new)

## Deviations from the brief

**Investigated but did not apply the pymupdf off-by-one rescale fix.** The dispatch message flagged a known quirk from Task 4 (`figures.crop_render`): `get_pixmap` rounds the transformed rect outward to whole pixels, so a zoom chosen to hit exactly 1400.0 can land on 1401px, and asked me to apply the same minimal fix here if `test_png_long_edge_is_1400` hit it for full-page renders.

I checked empirically before committing to any fix:
- `zoom = 1400 / max(720, 540) = 1400/720 = 1.9444444444444444` (Python float).
- `720 * zoom == 1400.0` and `540 * zoom == 1050.0` exactly (verified via `uv run python`).
- A direct render of a synthetic 720x540 page at this zoom via `page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))` produced a pixmap of exactly `1400 x 1050` — no off-by-one.
- `test_png_long_edge_is_1400` passed on the first try with the brief's unmodified code, and remained green after multiple full-suite runs.

Per the dispatch instructions ("If it doesn't occur, don't add anything"), I left `render_deck` as the brief's exact code, without the rescale branch that `crop_render` needed. The quirk in Task 4 arises from clipping to a `content_box` (fractional-point rect, non-trivial width/height ratio); full-page renders here start from the page's own integer-point dimensions (720x540, a 4:3 ratio), so the zoom's outward rounding happens to land exactly on integers for this fixture. This is a legitimate scope difference, not a suppressed test — no assertion was weakened.

## Self-review findings

- Implementation matches the brief's Step 3 code verbatim (after removing the speculative rescale fix I had initially added defensively, then reverted once I confirmed empirically it wasn't needed).
- Dependency direction respected: `render.py` imports only `workdir` and `figures.TARGET_LONG_EDGE`; nothing imports `cli` or `commands`.
- No extra code, no unused imports, docstrings kept as in the brief.
- Tests are exactly the brief's 7 tests, unmodified.

## Concerns

None. All 50 tests pass; no deviation weakens any assertion.
