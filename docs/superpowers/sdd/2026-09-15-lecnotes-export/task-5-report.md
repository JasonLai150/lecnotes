# Task 5 report: The export command and CLI

## What was implemented

`src/lecnotes/commands.py`:
- `_export_source(target: Path) -> Path` — resolves the CLI's `source` argument to the Markdown file to export. Raises `source_not_found` if `target` doesn't exist. For a directory: raises `unsupported_format` if it isn't a lecnotes workdir; raises `not_finished` if `out/<deck>.md` doesn't exist yet, or if `NOTES.md` exists and its text differs from the assembled `out/<deck>.md` (stale finish); otherwise returns the assembled Markdown path. For a file: raises `unsupported_format` unless its suffix (case-insensitive) is `.md`; otherwise returns it as-is.
- `export(target: Path, fmt: str, out: Path | None = None) -> dict` — resolves the source, reads the Markdown, finds local images via `markdown_doc.local_images`, and validates *before writing anything*: `missing_images` first (raises `image_not_found` with the sorted-unique `missing` list in `detail`), then for `fmt == "notion"` only, `export_notion.images_outside` (raises `image_outside_root` with `outside` in `detail`). On success, writes to `out` if given, else a default path next to the source (`<stem>.html` or `<stem>-notion.zip`), via `export_html.render_html` (HTML, creating the destination's parent dir) or `export_notion.write_notion_zip` (Notion zip, which creates its own parent). Returns `{"ok": True, "format", "source", "output", "images": <count of distinct resolved paths>, "bytes": <output file size>}`.

`src/lecnotes/cli.py`:
- Imports `export` alongside `finish, prep`.
- New `export` subparser: positional `source` (`Path`), required `--to {html,notion}` (dest `fmt`), optional `-o/--out` (`Path`), `--json`.
- `_report_export(result)` — prints the output path, then `"  {n} image(s), {size}"` with size in KB (or MB at ≥1 MiB).
- `main`'s dispatch changed from `if prep / else finish` to `if prep / elif finish / else export`, so a third subcommand no longer falls into `finish`'s branch.

Every line of `commands.py` and `cli.py` added here is the brief's code verbatim (Steps 3 and 7); no deviation was needed.

## TDD evidence

**RED (Step 2)** — `tests/test_export.py` created verbatim from the brief (13 tests) before `commands.export` existed:

```
$ uv run pytest tests/test_export.py -v
...
ImportError while importing test module '.../tests/test_export.py'.
tests/test_export.py:6: in <module>
    from lecnotes.commands import export, finish, prep
E   ImportError: cannot import name 'export' from 'lecnotes.commands' (.../src/lecnotes/commands.py)
=========================== short test summary info ============================
ERROR tests/test_export.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.08s ===============================
```

Exactly the brief's Step 2 expectation.

**GREEN (Step 4, command layer)** — after adding `_export_source`/`export` to `commands.py`:

```
$ uv run pytest tests/test_export.py -v
...
============================== 13 passed in 0.49s ==============================
```

Also per Step 4, the static guard now fails as documented (three new codes have no `ERROR_SCENARIOS` entry yet):

```
$ uv run pytest tests/test_cli.py -v
...
E       AssertionError: assert {'conversion_...lid_pdf', ...} == {'conversion_...workdir', ...}
E         Extra items in the left set:
E         'image_outside_root'
E         'not_finished'
E         'image_not_found'
tests/test_cli.py:257: AssertionError
========================= 1 failed, 37 passed in 1.52s =========================
```

This is the exact, expected transitional failure the brief calls out between Step 4 and Step 5.

**RED (Step 6, CLI layer)** — added the `_finished`/`_not_finished`/`_image_not_found`/`_image_outside_root` scenario helpers, the three `ERROR_SCENARIOS` entries, and the four `test_export_*`/error-code tests to `tests/test_cli.py`, before the `export` subparser existed:

```
$ uv run pytest tests/test_cli.py -v
...
FAILED tests/test_cli.py::test_export_html_human_output - AssertionError: ass...
FAILED tests/test_cli.py::test_export_notion_json - AssertionError: assert 1 ...
FAILED tests/test_cli.py::test_export_requires_to - assert '--to' in "usage: ...
FAILED tests/test_cli.py::test_error_code_in_json_mode[not_finished] - json.d...
FAILED tests/test_cli.py::test_error_code_in_json_mode[image_not_found] - jso...
FAILED tests/test_cli.py::test_error_code_in_json_mode[image_outside_root] - ...
========================= 6 failed, 42 passed in 1.87s =========================
```

Each failure traces back to argparse's `invalid choice: 'export'` (a `_UsageError` before `export` was a registered subcommand), matching the brief's Step 6 expectation. (`test_export_rejects_unknown_format` happened to already return 1 at this point, since an unrecognized subcommand is also exit 1 — not a sign anything was implemented yet.)

**GREEN (Step 8)** — after adding the `export` subparser, `_report_export`, and the three-way dispatch to `cli.py`:

```
$ uv run pytest tests/test_cli.py tests/test_export.py -v
...
============================== 61 passed in 2.12s ==============================
```

Full suite, before and after:

```
$ uv run pytest -q   # before (baseline, on main before this task)
229 passed in 3.92s

$ uv run pytest -q   # after
252 passed in 4.43s
```

252 - 229 = 23 new tests: 13 in `test_export.py` + 4 new `test_export_*` functions in `test_cli.py` + 6 from the 3 new `ERROR_SCENARIOS` entries × 2 output modes (`test_error_code_in_json_mode` / `test_error_code_in_human_mode`). No warnings in either run.

## Files changed
- `src/lecnotes/commands.py` (modified) — added `_export_source`, `export`, and the three new imports (`export_html.render_html`, `export_notion.{images_outside, write_notion_zip}`, `markdown_doc.{local_images, missing_images}`).
- `src/lecnotes/cli.py` (modified) — `export` subparser, `_report_export`, updated import and dispatch.
- `tests/test_export.py` (new) — 13 tests, copied verbatim from the brief.
- `tests/test_cli.py` (modified) — 4 new scenario helpers (`_finished`, `_not_finished`, `_image_not_found`, `_image_outside_root`), 3 new `ERROR_SCENARIOS` entries, 4 new `test_export_*` tests, all copied verbatim from the brief.

## Deviations from the brief

None. The brief's code for `commands.py`, `cli.py`, `test_export.py`, and the `test_cli.py` additions was used verbatim. `from conftest import make_png` inside `_image_outside_root` imported cleanly (no `tests/__init__.py` is present, so pytest's default "prepend" import mode puts `tests/` on `sys.path`), so the brief's documented fallback (inlining `make_png` via `import pymupdf`) was not needed.

## Self-review findings

Read the diff with fresh eyes against the four criteria:
- **Completeness**: `export` covers all paths in the brief — workdir (finished / not-finished / stale-after-edit), direct `.md` file, missing source, non-`.md` file, plain non-workdir directory, missing images (all listed, none written), notion-only outside-root rejection (html still succeeds for the same file), `-o/--out` override with overwrite, and non-mutation of the source Markdown across repeated exports. CLI covers human output (path + image count line), `--json`, `--to` required, and rejection of an unknown `--to` value (argparse `choices`). All three new error codes are wired through both `--json` and human-error paths via the existing `LecnotesError` → `cli.main` machinery, with no new special-casing needed.
- **Quality**: `_export_source` centralizes workdir-vs-file resolution so `export` itself only deals with "a Markdown path exists"; validation in `export` happens fully before any write (missing images, then outside-root for notion), matching the global constraint that all outputs overwrite only after validation passes. `_report_export`'s KB/MB formatting mirrors the existing reporters' style (`_report_prep`, `_report_finish`).
- **Discipline**: no code beyond the brief; the three-way `if/elif/else` dispatch in `cli.main` is the minimal change from the prior two-way `if/else`; no new runtime dependencies.
- **Testing**: TDD followed at both layers (command-level RED/GREEN, then CLI-level RED/GREEN) with the brief's own documented transitional-failure step (`test_every_raised_error_code_has_a_cli_scenario`) observed exactly as predicted; tests exercise real behavior (real zip/HTML output read back, real PNG fixtures, no mocking of `export` internals); full suite green with no warnings both before and after.

No issues found; nothing changed during self-review.

## Concerns

None. Implementation matches the brief exactly; both TDD phases produced the exact expected failures before implementation, and the full suite is green with no warnings.

---

## Fix round 1 (review findings)

Review found one Critical and one Important issue; everything else was approved.

1. **CRITICAL** — nothing prevented `dest == source`. `export(md, "html", out=md)` (or `notion`) returned `ok` and silently overwrote the source Markdown with the rendered output — for a workdir export this destroyed `out/<deck>.md`. Violated the global constraint that exporters never modify the input Markdown; the existing `test_exporters_never_modify_the_markdown` only covered the default output paths, so it didn't catch this.
2. **IMPORTANT** — `export(md, "html", out=existing_dir)` raised an uncaught `IsADirectoryError` (from `Path.write_text` for html, or `Path.replace` inside `write_notion_zip` for notion). In human CLI mode this surfaced as a raw traceback instead of `error: ...` with exit 1.

**Controller ruling implemented:** a new error code `invalid_output` (exit 1, the existing default since it isn't in `errors._DEPENDENCY_CODES`). In `commands.export`, `dest` is now computed once — still branching on `fmt` only to pick the default suffix (`.html` vs `-notion.zip`) — *before* either format's write step. Immediately after computing `dest` and before any write: if `dest.resolve() == source.resolve()`, raise `invalid_output` ("exporting to {dest} would overwrite the Markdown being exported; pass a different -o path"); elif `dest.is_dir()`, raise `invalid_output` ("{dest} is a directory; -o must be a file path"). Both carry `path=str(dest)` in `detail`. Validation order is preserved and extended: `image_not_found` → (notion only) `image_outside_root` → `invalid_output`, identically for both formats since the checks now sit after the format branch merges back into one `dest` variable.

### What changed
- `src/lecnotes/commands.py` — `export`: split the old `if fmt == "notion": ... write ... elif fmt == "html": ... write ...` into two passes. First pass (unchanged format-specific validation, e.g. `image_outside_root`) now only computes `dest` per format instead of also writing. A new shared block then does the two `invalid_output` checks against that one `dest`. A second, minimal `if fmt == "notion": write_notion_zip(...) else: render_html(...)` performs the actual write. No behavior changed for any previously-passing case; `dest`'s value and the final returned dict are identical to before for every path that isn't one of the two new rejections.
- `tests/test_export.py` — added `test_out_equal_to_source_is_rejected` (parametrized `html`/`notion`; asserts `invalid_output` and that the `.md` bytes are byte-for-byte unchanged), `test_out_equal_to_workdir_output_is_rejected` (workdir export with `-o` pointed at its own `out/<deck>.md`, via the `finished` fixture), and `test_out_is_existing_directory_is_rejected` (parametrized `html`/`notion`; asserts `invalid_output` and that nothing was created inside the target directory).
- `tests/test_cli.py` — added scenario helper `_invalid_output` (a `.md` exported with `-o` pointing at itself) and the `"invalid_output": (_invalid_output, 1)` entry in `ERROR_SCENARIOS`, so the static guard (`test_every_raised_error_code_has_a_cli_scenario`) and both `test_error_code_in_{json,human}_mode[invalid_output]` cover it automatically.

### TDD evidence

**RED** — wrote the covering tests above against the *pre-fix* `commands.py` (temporarily restored via `git stash push -- src/lecnotes/commands.py`, tests kept):

```
$ uv run pytest tests/test_export.py -k "out_equal_to_source or out_equal_to_workdir_output or out_is_existing_directory" -v
...
FAILED tests/test_export.py::test_out_equal_to_source_is_rejected[html]
FAILED tests/test_export.py::test_out_equal_to_source_is_rejected[notion]
FAILED tests/test_export.py::test_out_equal_to_workdir_output_is_rejected
FAILED tests/test_export.py::test_out_is_existing_directory_is_rejected[html] - IsADirectoryError: [Errno 21] Is a directory: '.../somedir'
FAILED tests/test_export.py::test_out_is_existing_directory_is_rejected[notion] - IsADirectoryError: [Errno 21] Is a directory: '.../somedir.tmp' -> '.../somedir'
======================= 5 failed, 13 deselected in 0.27s =======================

$ uv run pytest tests/test_cli.py -k invalid_output -v
...
FAILED tests/test_cli.py::test_error_code_in_json_mode[invalid_output] - AssertionError: assert 0 == 1
     ({"ok": true, "format": "html", ..., "output": ".../n.md", ...} — the source .md, overwritten)
FAILED tests/test_cli.py::test_error_code_in_human_mode[invalid_output] - AssertionError: assert 0 == 1
======================= 2 failed, 48 deselected in 0.13s =======================

$ uv run pytest tests/test_cli.py -k test_every_raised_error_code_has_a_cli_scenario -v
...
FAILED tests/test_cli.py::test_every_raised_error_code_has_a_cli_scenario
   Extra items in the right set: 'invalid_output'
```

This directly reproduced both review findings: the JSON payload shows `"ok": true` with `output` pointing at the overwritten `n.md` (Critical), and the directory case raised a raw `IsADirectoryError` deep inside `pathlib`/`write_notion_zip` rather than a `LecnotesError` (Important).

**GREEN** — restored the fix (`git stash pop`) and reran:

```
$ uv run pytest tests/test_export.py tests/test_cli.py -v
...
============================== 68 passed in 2.13s ==============================
```

68 = the prior 61 (test_export.py 13 + test_cli.py 48) + 7 new (5 in test_export.py + 2 in test_cli.py's both-modes `invalid_output` parametrization; the static guard was already counted in the 48).

Full suite, once, after the fix:

```
$ uv run pytest -q
259 passed in 4.47s
```

259 - 252 = 7, matching the 7 new tests. No warnings.

### Self-review

- **Completeness**: both findings' exact repro cases are now covered (same-as-source for both formats, workdir's own `out/<deck>.md` via the workdir path, and pre-existing directory for both formats), plus confirmation that nothing is written/created in each rejected case.
- **Quality**: `dest` computation and the write step are now separate, minimal, format-only branches around one shared validation block — no duplicated validation logic between html and notion, matching the controller's ruling verbatim.
- **Discipline**: no scope creep — did not touch `export_html.py` or `export_notion.py` (the bug and fix are entirely in `commands.export`'s ordering); did not add any check beyond the two the ruling specified.
- **Testing**: RED reproduced via a genuine revert-and-rerun (`git stash`) rather than reasoning about it, so the failure evidence above is real, not inferred; GREEN and the full suite were run after restoring the fix.

### Concerns

None. Both findings are fixed exactly per the controller's ruling; no further deviations.
