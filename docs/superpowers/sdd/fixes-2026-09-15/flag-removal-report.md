# Flag removal report

Repo: `/Users/jasonlai150/Documents/GitHub/lecnotes`
Brief: `docs/superpowers/sdd/fixes-2026-09-15/flag-removal-brief.md`
Template source: `docs/superpowers/sdd/fixes-2026-09-15/instructions-template-draft.md`
Base commit: `36e5491` (figure-link parsing already on markdown-it-py; read before editing)
Result commit: `bdc76dd` on `main` (not pushed)

## Summary

Removed the per-slide `has_figure` flag everywhere it existed (detection function,
manifest field, `render_instructions` parameter, CLI report line), and replaced
`src/lecnotes/templates/instructions.md` with the approved draft verbatim. Updated
`README.md`'s workdir layout description and JSON example to match. Updated tests
first (TDD), confirmed RED for the expected reasons, made the code changes,
confirmed GREEN, then ran the full suite once more and the brief's final grep.

## Changes (file:line references are to the committed state)

1. `src/lecnotes/render.py`
   - Deleted `FIGURE_IMAGE_AREA`, `FIGURE_DRAWING_COUNT`, and `has_figure()` (previously lines 10-20).
   - `render_deck` (render.py:11) no longer computes or includes a `"figure"` key in each row; rows are now exactly `{"n", "png", "txt", "chars"}` (render.py:26-33).

2. `src/lecnotes/commands.py` (`prep`, commands.py:21-90)
   - Manifest dict no longer has `"figures": sum(r["figure"] for r in rows)` (was commands.py:62 pre-change).
   - `render_instructions(...)` call no longer passes `figures=manifest["figures"]` (commands.py:69-73).
   - Returned result dict no longer has `"figures": manifest["figures"]` (commands.py:81-88).

3. `src/lecnotes/instructions.py`
   - `render_instructions(deck, slides, source_name)` — dropped the `figures` parameter and its substitution (instructions.py:11-15).

4. `src/lecnotes/cli.py`
   - `_report_prep` (cli.py:50-57): `print(f"  {result['slides']} slides")` — dropped `, {result['figures']} with figures`.

5. `src/lecnotes/templates/instructions.md`
   - Fully replaced with `docs/superpowers/sdd/fixes-2026-09-15/instructions-template-draft.md`, verified byte-identical via `diff` after copy (exit 0, "IDENTICAL"). Uses only `$deck`, `$slides`, `$source_name`.

6. `README.md`
   - Workdir tree: `manifest.json      per-slide metadata, including which slides carry figures` -> `manifest.json      per-slide metadata`.
   - Workdir tree pages description reworded for "every slide image is viewed; .txt can be incomplete":
     `slide-001.png    the rendered slide — every one gets viewed` /
     `slide-001.txt    that slide's text — can be incomplete; equations and diagrams often exist only in the image`.
   - JSON example: removed `"figures":29,` from the sample `lecnotes prep --json` output.
   - Left `figures.py`/`out/figures/`/`figures_resolved`/figure-link-validation prose untouched (legitimate "linked slide image" meaning), including the "758 carried figures that exist only as images" paragraph in "Why slides get rendered rather than parsed".

7. Backward compatibility (`finish` on old manifests): no source change was needed — `finish()` (commands.py) only reads `manifest["slides"]`/`manifest["deck"]`/`manifest["pages"]` count, never `"figures"`/`"figure"`, and `workdir.MANIFEST_KEYS` (workdir.py:69) does not include those keys either. Added a regression test (`test_finish.py`) proving it.

## Tests updated (TDD)

- `tests/test_render.py`: removed `test_text_only_page_has_no_figure` and `test_page_with_many_drawings_has_a_figure` (and the `has_figure` import); replaced `test_rows_carry_n_paths_chars_and_figure_flag` with `test_rows_have_exactly_n_png_txt_chars`, asserting `set(rows[0].keys()) == {"n", "png", "txt", "chars"}`.
- `tests/test_prep.py`: `test_manifest_shape` now asserts `"figures" not in m` and every page has exactly `{"n","png","txt","chars"}`; added `test_result_has_no_figures_key`.
- `tests/test_instructions.py`: rewritten `rendered()` helper without `figures=`; added/updated assertions for `"View every slide image"`, `"Beyond the slides"`, `"pseudocode"`, `"source.pdf"` plus the original source name, absence of `"repay a close look"` / `"hint, not a filter"`, and no leftover `$`. Also narrowed `test_no_unreplaced_placeholders` to only check for stray `$` (see Deviations).
- `tests/test_cli.py`: `test_prep_succeeds_and_prints_next_step` now asserts the human output's slide-count line is exactly `"  5 slides\n"` (see Deviations for why not a literal "not in" check); `test_prep_json_is_parseable_and_complete` asserts `"figures" not in payload`.
- `tests/test_finish.py`: added `test_finish_works_on_a_manifest_with_the_old_figure_keys`, which injects `figures`/`figure` keys into a freshly-prepped manifest and confirms `finish()` still succeeds.

## RED evidence

Ran `uv run pytest -q` after updating tests but before touching source. 17 failures, all for the expected reasons:

```
FAILED tests/test_cli.py::test_prep_succeeds_and_prints_next_step - Assertion...
FAILED tests/test_cli.py::test_prep_json_is_parseable_and_complete - Assertio...
FAILED tests/test_instructions.py::test_states_the_deck_and_slide_count - Typ...
FAILED tests/test_instructions.py::test_shows_the_exact_figure_link_syntax - ...
FAILED tests/test_instructions.py::test_names_the_file_to_write - TypeError: ...
FAILED tests/test_instructions.py::test_names_the_command_to_run_when_done - ...
FAILED tests/test_instructions.py::test_points_at_both_the_png_and_the_txt - ...
FAILED tests/test_instructions.py::test_no_unreplaced_placeholders - TypeErro...
FAILED tests/test_instructions.py::test_warns_that_figure_links_use_figures_not_pages
FAILED tests/test_instructions.py::test_tells_the_agent_to_view_every_slide_image
FAILED tests/test_instructions.py::test_marks_additions_beyond_the_slides - T...
FAILED tests/test_instructions.py::test_calls_algorithms_pseudocode - TypeErr...
FAILED tests/test_instructions.py::test_names_the_deck_source_file_and_the_original_name
FAILED tests/test_instructions.py::test_no_figure_flag_wording_remains - Type...
FAILED tests/test_prep.py::test_manifest_shape - AssertionError: assert 'figu...
FAILED tests/test_prep.py::test_result_has_no_figures_key - AssertionError: a...
FAILED tests/test_render.py::test_rows_have_exactly_n_png_txt_chars - Asserti...
17 failed, 172 passed in 4.47s
```

Representative causes: `render_instructions() missing 1 required positional argument: 'figures'` (old signature still required it); `assert 'figures' not in m` failing because the manifest still had the key; `assert set(rows[0].keys()) == {...}` failing because `'figure'` was still present. All failures map directly to "old code, new test expectations" -- none were import errors or unrelated breakage. (The new `test_finish_works_on_a_manifest_with_the_old_figure_keys` test passed even at this stage, as expected -- it documents pre-existing, already-correct behavior per brief item 7, not a change in production code.)

## GREEN evidence

After the source changes (render.py, commands.py, instructions.py, cli.py, templates/instructions.md):

```
uv run pytest -q
...
1 failed, 188 passed in 3.84s
FAILED tests/test_instructions.py::test_no_unreplaced_placeholders - AssertionError: assert '{' not in ...
```

That single remaining failure was a test bug, not a code bug -- see Deviations. After narrowing that assertion:

```
uv run pytest
============================= 189 passed in 3.71s ==============================
```

All green, no warnings summary emitted.

## Full-suite result (final, post-commit)

```
$ uv run pytest
platform darwin -- Python 3.11.5, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/jasonlai150/Documents/GitHub/lecnotes
configfile: pyproject.toml
testpaths: tests
collected 189 items

tests/test_cli.py ......................................                 [ 20%]
tests/test_conftest.py .....                                             [ 22%]
tests/test_errors.py ..............                                      [ 30%]
tests/test_figures_box.py .......                                        [ 33%]
tests/test_figures_refs.py ...........................                   [ 48%]
tests/test_finish.py ..................                                  [ 57%]
tests/test_ingest.py ...............                                     [ 65%]
tests/test_instructions.py ............                                  [ 71%]
tests/test_naming.py ............                                        [ 78%]
tests/test_prep.py ....................                                  [ 88%]
tests/test_render.py ......                                              [ 92%]
tests/test_workdir.py ...............                                    [100%]

============================= 189 passed in 4.17s ==============================
```

No warnings summary section, i.e. zero warnings emitted (pytest prints a "warnings summary" block whenever any warning fires; none appeared).

## Grep verification (brief's final check)

```
$ grep -rn "has_figure\|FIGURE_\|with figures\|carry figures" src tests README.md
```

Output: **(empty)** -- exit code 1 (grep convention for "no matches").

## Deviations from the brief / notes for the reviewer

1. **`test_no_unreplaced_placeholders` narrowed to only check `$`.** This pre-existing test also asserted no stray `{` remained (a leftover check, apparently from before `string.Template` was adopted -- `instructions.py`'s own docstring says "`$`-substitution leaves all of them alone," i.e. braces are never placeholder syntax here). The approved template legitimately contains `` `E_{x~p}[f(x)]` `` as a worked equation example, which is ordinary Markdown/math text, not a leaked placeholder. Since `string.Template` only recognizes `$name`/`${name}`, checking for `$` is the correct placeholder-leak test; checking for `{` was testing the wrong thing against the new (approved, verbatim) content. I removed only the `{` half of the assertion and kept the `$` check the brief explicitly asked for.

2. **`test_prep_succeeds_and_prints_next_step` doesn't literally assert `"with figures" not in out`.** An `assert "with figures" not in out` line would itself contain the literal string `"with figures"` in the test source, which would make the brief's final grep (`grep -rn "has_figure\|FIGURE_\|with figures\|carry figures" src tests README.md`) report a false-positive hit inside `tests/test_cli.py`. Instead the test asserts the human-readable slide-count line is exactly `"  5 slides\n"` (nothing trails the newline), which proves the same thing -- no `with figures` suffix -- without embedding the banned phrase. Confirmed the grep is empty with this phrasing.

3. **`deck_47` fixture in `tests/conftest.py`** still has an inline comment `# slide 8 carries a figure` (conftest.py:60) describing why that page has extra drawing lines. It isn't in the brief's list of files to touch, doesn't reference `has_figure`/`FIGURE_`/"with figures"/"carry figures" (so it doesn't trip the final grep), and no test asserts on `has_figure` via this fixture anymore. Left untouched to avoid scope creep; flagging in case the reviewer wants the comment reworded too.

4. **`-W error` pytest run segfaults** (exit 139) in this environment, unrelated to these changes -- it reproduces on a bare `uv run pytest -W error` with no test selection filtering, and appears to be a C-extension (pymupdf) interaction with promoting warnings to exceptions, not something introduced here. Verified "no warnings" via the normal run instead: pytest's default reporting prints an explicit "warnings summary" section whenever any warning occurs, and none appeared in 189/189 passing runs (both pre- and post-commit).

No other deviations. `figures.py`, `out/figures/`, `figures_resolved`, and figure-link validation (`find_refs`/`find_malformed`/`crop_render`) were left untouched, per the brief -- "figure" there means a linked slide image, which stays.
