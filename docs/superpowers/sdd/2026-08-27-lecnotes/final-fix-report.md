# Final-review fix wave: report

Status: DONE_WITH_CONCERNS (all 12 items in; two small deviations and one open concern, listed at the end)

Baseline before the wave: 98 passed, 5 SWIG warnings plus a `sys:1:` SWIG warning at shutdown.
After: **177 passed, 0 warnings**.

All test commands were run from `/Users/jasonlai150/Documents/GitHub/lecnotes` with `~/.local/bin/uv run pytest -q -p no:warnings <files>`. `-p no:warnings` only kept the RED output readable before item 11 landed.

---

## 1. Agent contract: finish command

**Changes**
- `src/lecnotes/templates/instructions.md:50-54`: the "When you are done" section now says "Run this from inside this directory:" followed by `lecnotes finish .`. The `$workdir_name` placeholder is gone.
- `src/lecnotes/instructions.py:11`: `render_instructions(deck, slides, figures, source_name)`. The `workdir_name` parameter is removed.
- `src/lecnotes/commands.py`: the `workdir_name=` argument is dropped from the call site. `:90` sets `"next": f"lecnotes finish {shlex.quote(str(root))}"`.
- `src/lecnotes/__main__.py` (new file) is guarded by `if __name__ == "__main__": raise SystemExit(main())`.
- `src/lecnotes/cli.py:114` adds the same `__main__` guard.
- `README.md`:
  - Install now documents `uv tool install git+https://github.com/JasonLai150/lecnotes`, `uv tool install .` and `python -m lecnotes`.
  - Use now shows `lecnotes prep` and `lecnotes finish .` run from inside the workdir, and points at the shell-quoted `next` step for other locations.
  - Development now holds `uv sync`, `uv run pytest` and `uv run lecnotes`.
  - The error shape now includes `message`.

**Tests**
- `tests/test_instructions.py`:
  - `test_names_the_command_to_run_when_done` checks that `    lecnotes finish .\n` and "from inside this directory" are present and that `lec1.notes` is absent.
  - `test_no_unreplaced_placeholders` now also asserts that no `$` remains.
  - The `rendered()` helper no longer passes `workdir_name`.
- `tests/test_prep.py`:
  - `test_result_tells_the_agent_what_to_do_next` now expects `shlex.quote`.
  - `test_next_command_quotes_a_workdir_path_with_spaces` (new) uses `Fall 2026/lec 1.notes` and asserts `shlex.split(next) == ["lecnotes","finish",str(root)]`.
  - `test_written_instructions_say_to_finish_from_inside_the_workdir` (new).
- `tests/test_cli.py`:
  - `test_runs_as_a_python_module[lecnotes|lecnotes.cli]` runs `python -m ... --version` in a subprocess.
  - `test_module_entry_point_propagates_the_exit_code` runs `python -m lecnotes finish <tmp> --json`, expecting exit 1 and `not_a_workdir`.

**RED** (`pytest tests/test_instructions.py tests/test_prep.py tests/test_cli.py`)
```
E       TypeError: render_instructions() missing 1 required positional argument: 'workdir_name'   (x7)
E         + lecnotes finish /private/var/.../test_next_command_quotes_a_wor0/Fall 2026/lec 1.notes
E       AssertionError: assert 'lecnotes finish .\n' in '...nish somewhere else\n\n...'
E       AssertionError: .../python: No module named lecnotes.__main__; 'lecnotes' is a package and cannot be directly executed
E       AssertionError: assert 'lecnotes 0.1.0' in ''          (python -m lecnotes.cli: no guard, prints nothing)
E           json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
12 failed, 31 passed in 1.33s
```
**GREEN** (same command): `43 passed in 1.38s`

## 2. Workdir identity

**Changes**
- `src/lecnotes/workdir.py:67`: `MANIFEST_KEYS = frozenset({"deck","slides","pages","rendered_long_edge"})`.
- `src/lecnotes/workdir.py:70-77`: `is_workdir` reads and parses the manifest. It returns False on `OSError`/`UnicodeDecodeError`/`ValueError` (which includes JSONDecodeError), and otherwise returns `isinstance(data, dict) and MANIFEST_KEYS <= data.keys()`.
- `require_workdir` still raises `not_a_workdir`; its message now reads "no valid manifest.json".

**Tests**
- `tests/test_workdir.py`:
  - `test_is_workdir_requires_a_manifest` now saves a valid manifest (`VALID_MANIFEST`).
  - `test_is_workdir_rejects_a_manifest_that_is_not_ours` is new and parametrized over: foreign `{"name": "my pwa"}`, a missing key, `{not json`, a JSON array, and an empty file.
  - Also new: `test_is_workdir_rejects_undecodable_bytes`, `test_is_workdir_rejects_a_manifest_directory` and `test_require_workdir_raises_on_a_foreign_manifest`.
- `tests/test_prep.py`: `test_force_refuses_a_directory_with_a_foreign_manifest` sets up `manifest.json` = `{"name":"my pwa"}` plus `pages/index.tsx`. `prep --force -o` raises `workdir_exists`, and the file tree and file contents are unchanged afterwards.
- `tests/test_finish.py`: `test_directory_with_a_manifest_that_is_not_ours_is_refused[foreign|unparseable]` expects `not_a_workdir`.
- **Updated existing test:** `tests/test_prep.py::test_force_re_renders_the_rest` used to write `{}` into the manifest and then run `--force`. Under the new identity rule that dir is no longer a workdir, so the test now writes a valid-shaped stale manifest (`slides: 99`) and checks that `--force` restores `slides == 1`. The test's intent is unchanged.

**RED** (`pytest tests/test_workdir.py tests/test_prep.py tests/test_finish.py`)
```
E       AssertionError: assert True is False  (is_workdir on each foreign/bad manifest, x6)
E       Failed: DID NOT RAISE LecnotesError   (require_workdir foreign; prep --force on the PWA dir -- it deleted pages/)
E       KeyError: 'slides'                    (finish on {"name": "my pwa"})
E           json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes
10 failed, 31 passed in 1.41s
```
**GREEN**: `41 passed in 1.36s`

## 3. prep validates before touching disk

**Changes**
- `src/lecnotes/ingest.py:81-82`: a single up-front `if not path.is_file(): raise LecnotesError("source_not_found", ...)` runs before any extension handling. It replaces the two duplicated `unsupported_format` "no such file" branches.
- `src/lecnotes/ingest.py:54-74`: new `_check_pdf(pdf, source)`. It opens the PDF with pymupdf and raises `invalid_pdf` in three cases: an open failure, `needs_pass`, or `page_count < 1`. It is called at `:103` for both given and converted PDFs, inside `resolve_source`. `commands.prep` calls `resolve_source` before any `root` check or disk write.
- `src/lecnotes/render.py:25-28`: `pages_dir(...).mkdir` now runs only after `pymupdf.open` succeeds.
- `src/lecnotes/commands.py:51-54`: the copy into `source.pdf` is skipped when `dest.exists() and os.path.samefile(info.pdf, dest)`.

**Tests**
- `tests/test_ingest.py`:
  - `test_missing_file_is_source_not_found[nope.pdf|nope.pptx|nope.ppt]` replaces the old `test_missing_file_is_a_usage_error`, which asserted `unsupported_format`.
  - Also new: `test_corrupt_pdf_is_invalid_pdf`, `test_zero_page_pdf_is_invalid_pdf` (a hand-written zero-page PDF, which pymupdf opens with `page_count == 0`), `test_password_protected_pdf_is_invalid_pdf` and `test_converted_pdf_that_will_not_open_is_invalid_pdf`.
- `tests/test_render.py`: `test_unopenable_pdf_creates_no_pages_dir`.
- `tests/test_prep.py`:
  - `test_missing_source_leaves_nothing_behind`.
  - `test_corrupt_pdf_fails_before_creating_the_workdir`: `broken.pdf` = `b"not a pdf"` raises `invalid_pdf` and `broken.notes` does not exist. A valid PDF is then synthesized at the same path, and prep to the same target succeeds.
  - `test_force_with_a_corrupt_pdf_leaves_the_existing_workdir_intact`.
  - `test_force_from_the_workdirs_own_source_pdf` runs `prep(lec1.notes/source.pdf, out=lec1.notes, force=True)`.

**RED** (`pytest tests/test_ingest.py tests/test_render.py tests/test_prep.py`)
```
E       AssertionError: assert 'unsupported_format' == 'source_not_found'   (x4)
E       Failed: DID NOT RAISE LecnotesError                                  (corrupt / zero-page / password / converted-garbage)
E       AssertionError: assert not True  (where True = .../wd/pages.exists)
E                   pymupdf.FileDataError: Failed to open file '.../broken.pdf' as type pdf.   (x2, raw pymupdf error escaped prep)
E           shutil.SameFileError: ... lec1.notes/source.pdf and ... lec1.notes/source.pdf are the same file
12 failed, 28 passed in 2.38s
```
**GREEN**: `40 passed in 0.73s`

CLI check on a real corrupt file, run from the scratchpad:
```
$ uv --project ... run lecnotes prep broken.pdf --json
{"ok": false, "error": "invalid_pdf", "message": "broken.pdf could not be opened as a PDF (Failed to open file 'broken.pdf' as type pdf.)", "path": "broken.pdf"}
exit=1
$ ls -d broken.notes
ls: broken.notes: No such file or directory
```

## 4. Deck-name slug

**Change**
- `src/lecnotes/naming.py:15`: `re.sub(r"[\W_]+", "-", name.casefold()).strip("-") or FALLBACK`, with `FALLBACK = "deck"` at `:10`.

**Tests**
- `tests/test_naming.py::test_slugify` keeps all existing cases and adds:
  - `Übung 3` → `übung-3`
  - `讲义 第一讲` → `讲义-第一讲`
  - `snake_case_deck` → `snake-case-deck`
  - `!!!` → `deck`
  - `""` → `deck`

**RED** (`pytest tests/test_naming.py tests/test_finish.py`)
```
E       AssertionError: assert 'bung-3' == 'übung-3'
E       AssertionError: assert '' == '讲义-第一讲'
E       AssertionError: assert '' == 'deck'      (x2)
4 failed, 19 passed in 1.10s
```
**GREEN**: `23 passed in 1.06s`

## 5. JSON errors carry the message

**Change**
- `src/lecnotes/errors.py:24`: `{"ok": False, "error": self.code, "message": self.message, **self.detail}`.

**Tests**
- `tests/test_errors.py::test_to_dict_carries_the_message_and_merges_detail` (renamed, now expects `message`). The exit-code parametrization now also covers `figure_malformed`, `source_not_found`, `invalid_pdf` and `internal_error`.
- `tests/test_cli.py::test_validation_failure_exits_1_with_json_error`: the exact-dict assertion now includes `"message": "NOTES.md references slides that are not in this deck: 91 (deck has 5)"`.

**RED** (`pytest tests/test_errors.py tests/test_cli.py tests/test_ingest.py`)
```
E         Right contains 1 more item:
E         {'message': 'bad ref'}
E         Right contains 1 more item:
E         {'message': 'NOTES.md references slides that are not in this deck: 91 (deck '
E                     'has 5)'}
```
(These two failures were part of the same RED run as items 8 and 9: `5 failed, 32 passed`.) **GREEN**: `37 passed in 0.54s`

## 6. Malformed figure links

**Changes**
- `src/lecnotes/figures.py`:
  - `:74`: `REF_RE = r"!\[([^\]]*)\]\(figures/slide-(\d{3}|[1-9]\d{3,})\.png\)"`. This is widened past 999; see Deviation A for why it is not the literal `\d{3,}`.
  - `:78-79`: `IMAGE_RE = r"!\[[^\]]*\]\(([^)]*)\)"` and `SLIDE_PNG_RE = r"slide-\d+\.png"`.
  - `:87-97`: `find_malformed(markdown) -> list[str]`. For each image whose target contains `slide-\d+\.png` but whose full markup does not fullmatch `REF_RE`, the target is recorded, in document order and de-duplicated.
- `src/lecnotes/commands.py:112-122`: `finish` raises `figure_malformed` with `bad_links=[...]` before the out-of-range check. Both checks happen before anything is written, and the order is documented in a test.
- `src/lecnotes/templates/instructions.md:43-44`: added one sentence: "The path is `figures/`, not `pages/`, with no `./` prefix and no link title. Any other form of slide image link is rejected."

**Tests**
- `tests/test_figures_refs.py`:
  - `test_slide_numbers_past_999_are_found` (`slide-1000.png` → `[1000]`) and `test_over_padded_number_is_not_a_ref`.
  - `test_malformed_slide_links_are_reported` is parametrized over `pages/slide-002.png`, `./figures/slide-003.png`, `figures/slide-5.png`, `figures/slide-001.png "t"`, `figures/slide-0001.png` and `out/figures/slide-004.png`.
  - `test_well_formed_and_unrelated_links_are_not_malformed` covers `figures/slide-001.png`, `slide-1000.png`, `assets/logo.png`, prose mentions, a plain non-image link, and an empty document.
  - `test_malformed_targets_are_in_document_order_and_deduplicated`.
- `tests/test_finish.py`:
  - `test_malformed_figure_link_is_named` checks `bad_links == ["pages/slide-002.png", "figures/slide-3.png"]` and that `out/` is not created.
  - `test_malformed_links_are_reported_before_out_of_range_ones` documents the order: malformed wins, and nothing is written.
- `tests/test_instructions.py::test_warns_that_figure_links_use_figures_not_pages`.

**RED**
```
$ pytest tests/test_figures_refs.py tests/test_finish.py tests/test_instructions.py
E   ImportError: cannot import name 'find_malformed' from 'lecnotes.figures'
1 error in 0.07s
$ pytest tests/test_finish.py tests/test_instructions.py
E       Failed: DID NOT RAISE LecnotesError
E       AssertionError: assert 'figure_out_of_range' == 'figure_malformed'
E       AssertionError: assert 'not `pages/`' in '# Write the notes for `lec1`...'
3 failed, 19 passed in 1.29s
```
**GREEN** (all three files): `44 passed in 1.29s`

## 7. Every error code in both output modes

**Tests** (`tests/test_cli.py:163-280`)
- `ERROR_SCENARIOS` maps each code to a setup function that returns argv, plus the expected exit code. It covers all ten codes: `source_not_found`, `unsupported_format` (`.key`), `invalid_pdf`, `missing_converter` (monkeypatched `which`), `conversion_failed` (monkeypatched `which` and `subprocess.run`), `workdir_exists`, `not_a_workdir`, `notes_empty`, `figure_out_of_range` and `figure_malformed`.
- `test_error_code_in_json_mode[code]` checks the exit code, `ok` false, `error == code`, and a non-empty `message`.
- `test_error_code_in_human_mode[code]` checks the exit code, empty stdout, and non-empty stderr.
- `test_every_raised_error_code_has_a_cli_scenario` scans `src/lecnotes/**/*.py` for `LecnotesError("<code>"` and asserts that set equals the scenario keys, so a future code can't be added without coverage.
- `internal_error` is not in that scan because it is not a `LecnotesError`. Items 8's tests cover it.

**RED**: this is coverage for behavior implemented under items 2-6, so the tests passed as soon as they were written. For honest RED evidence I ran the new `tests/test_cli.py` against the pre-wave commit `b2dabb4` in a throwaway worktree (removed afterwards):
```
$ git worktree add $SP/prewave b2dabb4 && cp tests/test_cli.py $SP/prewave/tests/
$ PYTHONPATH=$SP/prewave/src .venv/bin/python -m pytest -q -p no:warnings tests/test_cli.py -k "error_code or every_raised"
FAILED test_every_raised_error_code_has_a_cli_scenario
FAILED test_error_code_in_json_mode[source_not_found|unsupported_format|invalid_pdf|missing_converter|conversion_failed|workdir_exists|not_a_workdir|notes_empty|figure_out_of_range|figure_malformed]
FAILED test_error_code_in_human_mode[invalid_pdf|figure_malformed]
13 failed, 8 passed, 17 deselected in 2.03s
```
**GREEN** (current tree): `pytest tests/test_cli.py` gives `38 passed in 1.33s`.

## 8. JSON contract on unexpected errors

**Change**
- `src/lecnotes/cli.py:91-105`: `except Exception`. In `--json` mode it prints `{"ok": false, "error": "internal_error", "message": "<Type>: <str>"}` and returns 1. In human mode it re-raises.

**Tests**
- `tests/test_cli.py::test_unexpected_exception_in_json_mode_is_internal_error` monkeypatches `lecnotes.cli.prep` to raise `RuntimeError("disk on fire")` and checks the exact dict.
- `test_unexpected_exception_in_human_mode_propagates` is a guard that already passed before the change.

**RED**: `E       RuntimeError: disk on fire`, part of the `5 failed, 32 passed` run above. **GREEN**: `37 passed`.

## 9. conversion_failed diagnostic

**Change**
- `src/lecnotes/ingest.py:14` and `:36-50`: keeps the `subprocess.run` result, decodes `proc.stderr` with `errors="replace"`, and stores the last `STDERR_TAIL_LINES = 20` lines in the error detail as `stderr`.

**Tests**
- `tests/test_ingest.py::test_pptx_conversion_that_emits_no_pdf_fails_clearly`: the fake `run` now returns `SimpleNamespace(returncode, stdout=b"", stderr=b"...")`, and the test asserts the text appears in `detail["stderr"]`.
- `test_conversion_failed_keeps_only_the_tail_of_stderr` (new) feeds 100 lines plus a `\xff` byte and asserts exactly 20 lines, starting at `line 82` and ending with `bad � byte`.
- `test_pptx_conversion_success`: the fake `run` now returns an object as well.

**RED**: `E       KeyError: 'stderr'` (x2). **GREEN**: `37 passed`.

## 10. Packaging

**Change**
- `pyproject.toml:21-22`: `[tool.hatch.build.targets.sdist] exclude = ["docs/superpowers/sdd"]`.

**Evidence**: no test, since this is config. Checked by building the sdist before and after:
```
$ git stash push pyproject.toml && uv build --sdist -o $SP/dist-before
sdd entries before: 32
$ git stash pop && uv build --sdist -o $SP/dist
sdd entries after: 0
```

## 11. Pristine test output

**Change**
- `pyproject.toml:26-30`: `filterwarnings` ignores only `builtin type Swig\w+ has no __module__ attribute` and `builtin type swigvarlink has no __module__ attribute`, both as `DeprecationWarning`.

**RED** (`uv run pytest -q` before the change):
```
<frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute
<frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyObject has no __module__ attribute
<frozen importlib._bootstrap>:241: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
177 passed, 5 warnings in 3.39s
sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
```
**GREEN**: `177 passed in 3.24s`. `grep -ci "warn|swig"` over the full output gives 0, and the `sys:1:` shutdown line is gone too.

**Scope check**: I ran a throwaway probe test with this pyproject config. It emitted one unrelated `DeprecationWarning` and one SWIG-text warning. Only the unrelated one was reported (`2 passed, 1 warning`), so the filter is not a blanket ignore.

## 12. Slug end-to-end

**Test**
- `tests/test_finish.py::test_punctuated_deck_name_flows_through_to_the_output_file` preps `lec8-txn,cc.pdf`, writes notes with one figure link, runs finish, and asserts `result["output"]` is `.../lec8-txn-cc.md` and that `out/lec8-txn-cc.md` exists.

**RED/GREEN**: this test passed when first written, because the old ASCII slug already handled this name correctly. It is a regression guard for the new slug implementation, not a behavior change. It stayed green through item 4 (`23 passed`).

---

## Full suite

```
$ uv run pytest
platform darwin -- Python 3.11.5, pytest-9.1.1, pluggy-1.6.0
configfile: pyproject.toml
collected 177 items
tests/test_cli.py ......................................                 [ 21%]
tests/test_conftest.py .....                                             [ 24%]
tests/test_errors.py ..............                                      [ 32%]
tests/test_figures_box.py .......                                        [ 36%]
tests/test_figures_refs.py ......................                        [ 48%]
tests/test_finish.py ...............                                     [ 57%]
tests/test_ingest.py ...............                                     [ 65%]
tests/test_instructions.py .......                                       [ 69%]
tests/test_naming.py ............                                        [ 76%]
tests/test_prep.py ...................                                   [ 87%]
tests/test_render.py ........                                            [ 91%]
tests/test_workdir.py ...............                                    [100%]
============================= 177 passed in 3.44s ==============================
```
No warnings.

## Real-deck smoke run

Run from the scratchpad, `SP=/private/tmp/claude-501/-Users-jasonlai150-Documents-GitHub-4440/b8ce7be5-28b5-4a05-868b-6c0cf5495ca3/scratchpad`.

```
$ uv --project /Users/jasonlai150/Documents/GitHub/lecnotes run lecnotes prep /Users/jasonlai150/Documents/GitHub/4440/slides/lec13-b+tree.pdf -o "$SP/final smoke.notes" --json
{"ok": true, "workdir": "$SP/final smoke.notes", "deck": "lec13-b-tree", "slides": 52, "figures": 46, "notes_preserved": false, "instructions": "$SP/final smoke.notes/INSTRUCTIONS.md", "write_to": "$SP/final smoke.notes/NOTES.md", "next": "lecnotes finish '$SP/final smoke.notes'"}
exit=0

$ cd "$SP/final smoke.notes" && sed -n 50,57p INSTRUCTIONS.md
## When you are done

Run this from inside this directory:

    lecnotes finish .

That validates your figure links, crops and copies the figures, and assembles
`out/lec13-b-tree.md`.

$ printf '# B+ Trees\n\nFanout keeps the tree shallow.\n\n![a B+ tree node layout](figures/slide-007.png)\n' > NOTES.md
$ uv --project /Users/jasonlai150/Documents/GitHub/lecnotes run lecnotes finish . --json
{"ok": true, "workdir": ".", "deck": "lec13-b-tree", "output": "out/lec13-b-tree.md", "figures_resolved": 1}
exit=0
$ ls out out/figures
out: figures  lec13-b-tree.md
out/figures: slide-007.png            (PNG 1400x589)

$ printf '# B+ Trees\n\n![wrong dir](pages/slide-002.png)\n' > NOTES.md
$ uv --project /Users/jasonlai150/Documents/GitHub/lecnotes run lecnotes finish . --json
{"ok": false, "error": "figure_malformed", "message": "NOTES.md has slide image links not written as ![caption](figures/slide-NNN.png): pages/slide-002.png", "bad_links": ["pages/slide-002.png"]}
exit=1
$ uv --project /Users/jasonlai150/Documents/GitHub/lecnotes run lecnotes finish .
error: NOTES.md has slide image links not written as ![caption](figures/slide-NNN.png): pages/slide-002.png
exit=1
```

Extra checks:
- **`next` runs as-is through a shell.** I re-prepped with `--force --json` (NOTES.md was preserved) and ran the `next` string via `bash -c "$NEXT --json"`. The quoted path containing a space resolved, giving the expected `figure_malformed` and exit 1.
- **Self-source re-prep works.** `lecnotes prep "final smoke.notes/source.pdf" -o "final smoke.notes" --force` exited 0, `source.pdf` is byte-identical to the original deck (`cmp`), and NOTES.md was preserved. See Concern 1.
- **Module entry point.** `uv run python -m lecnotes --version` prints `lecnotes 0.1.0`.

## Commits (on main, not pushed; docs/superpowers/sdd not committed)

```
89749fa Carry the message in JSON errors; report internal_error and soffice stderr   (items 5, 8, 9)
61c9be0 Keep Unicode letters in deck names and fall back to 'deck'                   (items 4, 12)
a14e0a2 Recognize a workdir by its manifest's contents, not its filename             (item 2)
df55ecc Validate the source before prep touches disk                                 (item 3)
eeaf4b7 Reject malformed figure links and allow slide numbers past 999               (item 6)
7904e2e Tell the agent to run 'lecnotes finish .'; add python -m lecnotes            (item 1, README)
085db76 Cover every error code in both output modes; tidy packaging and test output  (items 7, 10, 11)
```

## Deviations

**A. `REF_RE` is `slide-(\d{3}|[1-9]\d{3,})\.png`, not the brief's literal `slide-(\d{3,})\.png`.**
- With `\d{3,}`, the link `figures/slide-0001.png` would count as a valid reference to slide 1.
- `finish` crops that slide to `out/figures/slide-001.png`, so the assembled document would contain a dangling image link and `finish` would report success.
- The amended spec says links must be "exactly `figures/slide-NNN.png`" and that numbers are "zero-padded to at least three digits (`slide-008.png`, `slide-1000.png`)", which is the form `f"{n:03d}"` produces. The narrower regex matches exactly those names.
- Every behavior the brief asked for holds: `slide-1000.png` works, and all the listed malformed and valid examples behave as specified.
- As a result, `slide-0001.png` is reported as `figure_malformed`. Tests: `test_over_padded_number_is_not_a_ref` and the `figures/slide-0001.png` case in `test_malformed_slide_links_are_reported`.

**B. `invalid_pdf` also covers password-protected PDFs** (`doc.needs_pass`).
- Such a PDF opens in pymupdf, but rendering fails with `ValueError: document closed or encrypted`, which would crash prep partway through the workdir.
- The spec defines `invalid_pdf` as "cannot be opened", and this falls under it. The fix is one branch in the same check. Test: `test_password_protected_pdf_is_invalid_pdf`.

**C. Existence is checked before extension handling for every input.**
- A missing `lec1.key` or `lec1.txt` now gives `source_not_found` rather than `unsupported_format`.
- That matches the spec table ("when the input path does not exist") and the brief's dedupe instruction. Existing tests for `.key` and unknown extensions create the file first, so they are unaffected.

## Concerns

1. **Re-prepping from the workdir's own `source.pdf` renames the deck to `source`.**
   - The deck name is derived from the input stem, so after `prep lec1.notes/source.pdf -o lec1.notes --force` the manifest has `deck: "source"` and `source: "source.pdf"`. `finish` would then write `out/source.md` instead of `out/lec1.md`. I reproduced this on the real deck: after the self-source re-prep, the manifest's deck is `source`.
   - The brief and amended spec only require that this case not fail on the self-copy, and that is what I implemented.
   - Keeping the old name, e.g. by reusing the existing manifest's `deck`/`source` when the input is the workdir's own `source.pdf`, is a design decision I left for you.
2. **`workdir_exists` is still checked after source resolution**, which is the existing order: a `.pptx` is converted before prep notices the target exists. This is harmless because nothing is written, but a conversion can be wasted. Not changed; it is outside the brief.
