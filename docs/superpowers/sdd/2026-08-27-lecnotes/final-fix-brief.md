# Final-review fix wave — brief

Repo: /Users/jasonlai150/Documents/GitHub/lecnotes. All 13 plan tasks are done (98 tests passing). A whole-branch review found the issues below. The spec has been amended to cover them: read the **"Amendments (2026-09-14, from the final whole-branch review)"** section at the end of `docs/superpowers/specs/2026-08-27-lecnotes-design.md` — it is binding and supersedes earlier spec text where they conflict.

Fix everything in the list below, test-first. Group into a few coherent commits (e.g. one per numbered item or natural cluster), not one giant commit.

## Required fixes

1. **Agent contract: finish command.**
   - `src/lecnotes/templates/instructions.md`: tell the agent to run `lecnotes finish .` from inside this directory. Remove the `$workdir_name` placeholder and its parameter from `render_instructions` and its call site; update tests/test_instructions.py (it currently asserts `lecnotes finish lec1.notes`).
   - `commands.prep` result `next`: `f"lecnotes finish {shlex.quote(str(root))}"`. Update the tests that assert `next`; add a test with a workdir path containing a space.
   - Add `src/lecnotes/__main__.py` so `python -m lecnotes` runs the CLI, and add an `if __name__ == "__main__": raise SystemExit(main())` guard to cli.py.
   - README: document `uv tool install git+https://github.com/JasonLai150/lecnotes` (or `uv tool install .`) as the way to install for real use, keep `uv sync`/`uv run` under Development, and make the "Use" section consistent with `lecnotes finish .` / the `next` field.

2. **Workdir identity.** `workdir.is_workdir(root)` returns True only if `manifest.json` is a file that parses as a JSON object containing keys `deck`, `slides`, `pages`, `rendered_long_edge`; bad JSON or missing keys → False (never raises). `require_workdir` keeps raising `not_a_workdir`. Tests: foreign `manifest.json` (e.g. `{"name":"my pwa"}`) with a `pages/index.tsx` → `prep --force -o <dir>` raises `workdir_exists` and deletes nothing; `finish` on that dir and on a dir with unparseable manifest JSON → `not_a_workdir` (no KeyError/JSONDecodeError). Existing test_workdir tests that save a minimal manifest like `{"deck": "d"}` and expect is_workdir True must be updated to save a valid manifest.

3. **prep validates before touching disk.**
   - Missing input path → new code `source_not_found` (exit 1) — replaces the current `unsupported_format` "no such file" raises in ingest.py (dedupe the two branches while there).
   - The PDF (given, or converted from pptx) must be opened with pymupdf and checked to have ≥1 page before the workdir is created or modified; failure → new code `invalid_pdf` (exit 1). A failed prep on a new target must leave no directory behind (test with a corrupt file, e.g. bytes `b"not a pdf"` saved as `broken.pdf`: raises `invalid_pdf`, `broken.notes` does not exist, and a subsequent successful prep of a valid file at the same target works).
   - Move `pages_dir(...).mkdir` in render.py after the document opens successfully (or rely on the up-front validation — but render.py must not create `pages/` for a PDF it can't open).
   - `prep --force` where the source is the workdir's own `source.pdf` (`prep lec1.notes/source.pdf -o lec1.notes --force`) must succeed: skip the copy when source and destination resolve to the same file. Test it.

4. **Deck-name slug.** Per the amended spec: casefold; runs of non-(Unicode letter or digit) characters, underscore included, → single `-`; strip `-`; empty → `deck`. Implementation hint: `re.sub(r"[\W_]+", "-", name.casefold()).strip("-") or "deck"`. Keep all existing test_naming cases passing and add: `Übung 3` → `übung-3`, `讲义 第一讲` → `讲义-第一讲`, `!!!` → `deck`, `""` → `deck`.

5. **JSON errors carry the message.** `LecnotesError.to_dict()` → `{"ok": False, "error": code, "message": message, **detail}`. Update test_errors.py and test_cli.py's exact-dict assertion.

6. **Malformed figure links.** In `finish`, detect any Markdown image `!\[[^\]]*\]\(([^)]*)\)` whose target contains `slide-\d+\.png` but whose full image markup does not match the strict reference regex → new code `figure_malformed` (exit 1) with detail `bad_links: [<the link targets, in document order, de-duplicated>]`. Check malformed and out-of-range before writing anything (malformed first, or both — your choice, but document it in a test). Put the detection function in figures.py next to `find_refs` (e.g. `find_malformed(markdown) -> list[str]`) with its own unit tests: `pages/slide-002.png`, `./figures/slide-003.png`, `figures/slide-5.png`, `figures/slide-001.png "t"` are malformed; `figures/slide-001.png` and `assets/logo.png` are not.
   Also widen the strict reference regex to `slide-(\d{3,})\.png` so slide 1000+ works; add a find_refs test for `slide-1000.png`.
   Update INSTRUCTIONS.md template wording if useful so the agent knows links must use `figures/`, not `pages/`.

7. **Every error code in both output modes.** A parametrized test in tests/test_cli.py driving `main()` for each spec error code that the CLI can reach in this environment — `source_not_found`, `unsupported_format`, `invalid_pdf`, `missing_converter` (monkeypatch `lecnotes.ingest.shutil.which`), `conversion_failed` (monkeypatch which + subprocess.run), `workdir_exists`, `not_a_workdir`, `notes_empty`, `figure_out_of_range`, `figure_malformed` — in both `--json` mode (exit code, stdout JSON `error` and non-empty `message`, empty stderr not required) and human mode (exit code, non-empty stderr, empty stdout).

## Also fix (small)

8. **JSON contract on unexpected errors.** In cli.py, when `--json` is set, catch any non-`LecnotesError` exception from the command and print `{"ok": false, "error": "internal_error", "message": "<ExceptionType>: <str>"}`, return 1. In human mode, let it propagate (traceback is fine for humans). Test with a monkeypatched `commands.prep` that raises `RuntimeError`.
9. **conversion_failed diagnostic.** Include the last ~20 lines of soffice stderr (decoded, errors="replace") in the error detail as `stderr`. Update the test's fake `subprocess.run` to return an object with `.stderr`/`.stdout` bytes.
10. **Packaging:** in pyproject.toml add `[tool.hatch.build.targets.sdist] exclude = ["docs/superpowers/sdd"]`.
11. **Pristine test output:** in `[tool.pytest.ini_options]` add a `filterwarnings` entry ignoring the pymupdf SWIG `DeprecationWarning`s (`builtin type Swig... has no __module__ attribute` / `swigvarlink`). Only those; don't blanket-ignore DeprecationWarning.
12. **Slug end-to-end:** a test that preps `lec8-txn,cc.pdf`, writes notes, runs finish, and asserts `out/lec8-txn-cc.md` exists.

## Out of scope — do NOT do
- Moving layout literals from commands.py/figures.py into workdir.py.
- Removing the `deck_47` fixture, the version duplication, symlink handling.
- Any change to the editorial prose of INSTRUCTIONS.md beyond what items 1 and 6 require.

## Constraints
- pymupdf stays the only runtime dependency. Python >= 3.11.
- Exit codes: 0 success, 1 usage/validation, 2 missing external dependency (only `missing_converter`, `conversion_failed`).
- `NOTES.md` is never overwritten by prep.
- cli.py: parsing, output shaping, exit codes only.
- Commit on main; do NOT push; do not commit docs/superpowers/sdd/. You MAY commit README.md.
- Commit messages end with `Co-Authored-By: Claude <your model name> <noreply@anthropic.com>` then `Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy`.
