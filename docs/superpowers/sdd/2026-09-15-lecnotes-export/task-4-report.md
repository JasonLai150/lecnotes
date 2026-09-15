# Task 4 report: Notion import zip

## What was implemented

`src/lecnotes/export_notion.py`, exposing:
- `TITLE_MAX = 100`
- `unwrap(markdown: str) -> str`
- `sanitize_filename(text: str) -> str`
- `split_title(markdown: str, fallback_stem: str) -> tuple[str, str]`
- `images_outside(images: list[LocalImage], base_dir: Path) -> list[str]`
- `write_notion_zip(markdown: str, images: list[LocalImage], base_dir: Path, dest: Path, fallback_stem: str) -> None`

Behavior (per the brief, implemented verbatim):
- `unwrap` parses with the shared `mdparse.PARSER`, tracks blockquote depth, and collects the `.map` line range of every `paragraph_open` token that is not inside a blockquote and spans more than one source line. For each such range (processed in reverse so earlier ranges' line indices stay valid), it joins continuation lines onto the previous line with a single space, except where the previous line already ends in two trailing spaces or a backslash (a hard break the author meant to keep). Only these paragraph ranges are touched, so fenced/indented code, tables, headings, and blockquotes are left byte-for-byte.
- `sanitize_filename` replaces `/ \ : * ? " < > |` with `-`, strips, caps at `TITLE_MAX`, strips again (so a cap landing on trailing whitespace doesn't leave it).
- `split_title` finds the first top-level (`token.level == 0`) `h1` `heading_open`, renders its inline children as plain text via `PARSER.renderer.renderInlineAsText`, and sanitizes that as the stem. If the sanitized stem is empty (whitespace-only heading) or the token has no `.map`, it falls back to `fallback_stem` with the markdown unchanged. Otherwise it deletes the heading's line range and returns the sanitized stem plus the remaining body (leading blank lines stripped).
- `images_outside` resolves `base_dir` and returns the `src` of every image whose resolved `path` is not `path.is_relative_to(base)`, in order.
- `write_notion_zip` calls `split_title`, then writes a zip to `dest.name + ".tmp"` containing `{stem}.md` (the body run through `unwrap`) and each de-duplicated image (`dict.fromkeys` collapses two srcs naming the same file, e.g. `figures/x.png` and `./figures/x.png`) at its path relative to `base_dir`, then atomically renames the tmp file onto `dest` (so a prior file at `dest` is fully overwritten and no `.tmp` leftover remains).

This module is a pure leaf: it raises nothing, and per its documented precondition (images exist, none outside `base_dir`) that validation is the caller's job in Task 5's `commands.export`, which calls `images_outside` first.

## TDD evidence

**RED** — wrote `tests/test_export_notion.py` (12 tests, copied verbatim from the brief) before creating the implementation module:

```
$ uv run pytest tests/test_export_notion.py -v
...
ERROR collecting tests/test_export_notion.py
ImportError while importing test module '.../tests/test_export_notion.py'.
Traceback:
  tests/test_export_notion.py:3: in <module>
    from lecnotes.export_notion import (
E   ModuleNotFoundError: No module named 'lecnotes.export_notion'
=========================== short test summary info ============================
ERROR tests/test_export_notion.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.05s ===============================
```

This is exactly the failure the brief's Step 2 specifies.

**GREEN** — after creating `src/lecnotes/export_notion.py` verbatim from the brief:

```
$ uv run pytest tests/test_export_notion.py -v
...
tests/test_export_notion.py::test_unwrap_joins_wrapped_paragraph_keeping_spans_intact PASSED [  8%]
tests/test_export_notion.py::test_unwrap_joins_list_item_continuations PASSED [ 16%]
tests/test_export_notion.py::test_unwrap_leaves_code_tables_headings_and_quotes_alone PASSED [ 25%]
tests/test_export_notion.py::test_unwrap_preserves_hard_breaks PASSED    [ 33%]
tests/test_export_notion.py::test_sanitize_filename PASSED               [ 41%]
tests/test_export_notion.py::test_split_title_uses_first_h1_and_removes_it PASSED [ 50%]
tests/test_export_notion.py::test_split_title_strips_inline_markup PASSED [ 58%]
tests/test_export_notion.py::test_split_title_falls_back_without_h1 PASSED [ 66%]
tests/test_export_notion.py::test_split_title_falls_back_when_title_sanitizes_to_empty PASSED [ 75%]
tests/test_export_notion.py::test_images_outside PASSED                  [ 83%]
tests/test_export_notion.py::test_write_notion_zip_layout PASSED         [ 91%]
tests/test_export_notion.py::test_write_notion_zip_overwrites PASSED     [100%]

============================== 12 passed in 0.11s ==============================
```

No deviation was needed: markdown-it-py's `.map` for list-item paragraph continuations and for an empty/whitespace-only ATX heading both matched the brief's tested expectations on the first run (all 12 tests passed without modification).

Full suite, before and after:

```
$ uv run pytest -q   # before (baseline, on main before this task)
217 passed in 4.06s

$ uv run pytest -q   # after
229 passed in 4.04s
```

229 - 217 = 12, matching the 12 new tests. No warnings in either run.

## Files changed
- `src/lecnotes/export_notion.py` (new) — `TITLE_MAX`, `unwrap`, `sanitize_filename`, `split_title`, `images_outside`, `write_notion_zip`.
- `tests/test_export_notion.py` (new) — 12 tests, copied verbatim from the brief.

## Deviations from the brief

None. The brief's code was implemented exactly as given, and every test passed on the first run against the installed markdown-it-py, so no markdown-it API-behavior workaround was needed.

## Self-review findings

Read the diff with fresh eyes against the four criteria:
- **Completeness**: matches the documented interface exactly (`TITLE_MAX`, `unwrap`, `sanitize_filename`, `split_title`, `images_outside`, `write_notion_zip`); respects the precondition (does not validate image existence/outside-ness itself — that's Task 5's `commands.export` job, which calls `images_outside` before this); handles wrapped paragraphs (top-level and list-item), hard breaks, code/table/heading/blockquote preservation, filename sanitization (including the all-whitespace-input edge case), H1-based title extraction with inline-markup stripping, fallback when no H1 or a heading sanitizes to empty, image de-duplication by resolved path, and atomic overwrite via a `.tmp` file + `replace`.
- **Quality**: names are clear (`unwrap`, `sanitize_filename`, `split_title`, `images_outside`, `write_notion_zip`); docstrings explain *why* (Notion's paragraph-merge-without-reparsing behavior motivating `unwrap`; Notion titling the page from the filename motivating `split_title`'s heading removal); reuses `markdown_doc.LocalImage` and the shared `mdparse.PARSER` rather than reimplementing parsing, keeping one source of truth.
- **Discipline**: no code beyond what the brief specifies; no new runtime dependencies (only stdlib `re`, `zipfile`, `pathlib`); leaf module raises nothing, matching the global constraint.
- **Testing**: TDD followed (RED confirmed for the correct reason — `ModuleNotFoundError`; then GREEN); tests exercise real behavior (real zip files read back with `zipfile`, real PNG fixtures via the `png` fixture, no mocking); full suite green with no warnings both before and after.

No issues found; nothing changed during self-review.

## Concerns

None. Implementation matches the brief exactly; all TDD steps behaved as specified with no API-assumption deviations to report.
