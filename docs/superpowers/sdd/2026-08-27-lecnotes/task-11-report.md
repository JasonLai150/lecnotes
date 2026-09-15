# Task 11 report: the `finish` command

## What was implemented

- `src/lecnotes/commands.py` — appended `finish(root: Path) -> dict`, and
  extended the existing `.figures` import from `TARGET_LONG_EDGE` to
  `TARGET_LONG_EDGE, crop_render, find_refs`. `finish`:
  1. Requires `root` to be a lecnotes workdir (`workdir.require_workdir`,
     `not_a_workdir` on failure).
  2. Loads the manifest and `NOTES.md`'s body. If the notes file is missing,
     empty, or still exactly the `NOTES_STUB` placeholder, refuses with
     `notes_empty` before anything else runs.
  3. Extracts every `figures/slide-NNN.png` reference via `find_refs` and
     validates all of them against `manifest["slides"]` *before* writing
     anything — collecting every out-of-range reference (not just the first)
     into `bad_refs` and raising `figure_out_of_range` if any exist. Because
     this check runs before `out/` is created or touched, a bad link leaves no
     `out/` directory behind at all.
  4. Only once validation passes: removes `out/figures` if it already exists
     (`shutil.rmtree`) and recreates it, so a rebuild cannot leave a prior
     run's figures behind, then re-creates it and crops each referenced slide
     into it via `crop_render`.
  5. Writes the notes body verbatim to `out/<deck>.md`.
  6. Returns `{"ok": True, "workdir", "deck", "output", "figures_resolved"}`.

- `tests/test_finish.py` — 10 tests, created verbatim from the brief's Step 1,
  covering: output document assembly, resolving and cropping a referenced
  figure, copying only the slides actually referenced, notes with no figure
  references still building (`figures_resolved == 0`), naming a single
  out-of-range reference in `bad_refs`, reporting every bad reference (not
  just the first, sorted), confirming `out/` doesn't exist at all when
  validation fails, refusing an unwritten (still-stub) `NOTES.md`, refusing a
  non-workdir root, and a rebuild clearing stale `out/figures` entries from a
  previous run.

## TDD evidence

**RED**

```
$ uv run pytest tests/test_finish.py -v
...
ImportError while importing test module '.../tests/test_finish.py'.
tests/test_finish.py:4: in <module>
    from lecnotes.commands import finish, prep
E   ImportError: cannot import name 'finish' from 'lecnotes.commands' (.../src/lecnotes/commands.py)
...
========================= 5 warnings, 1 error in 0.05s =========================
```

Expected failure reason, matching the brief's Step 2 exactly — `finish` didn't
exist yet in `commands.py`.

**GREEN**

```
$ uv run pytest tests/test_finish.py -v
tests/test_finish.py::test_assembles_the_output_document PASSED          [ 10%]
tests/test_finish.py::test_resolves_and_crops_referenced_figures PASSED  [ 20%]
tests/test_finish.py::test_only_referenced_slides_are_copied PASSED      [ 30%]
tests/test_finish.py::test_notes_with_no_figures_still_builds PASSED     [ 40%]
tests/test_finish.py::test_out_of_range_reference_is_named PASSED        [ 50%]
tests/test_finish.py::test_every_bad_reference_is_reported_not_just_the_first PASSED [ 60%]
tests/test_finish.py::test_nothing_is_written_when_validation_fails PASSED [ 70%]
tests/test_finish.py::test_unwritten_notes_are_refused PASSED            [ 80%]
tests/test_finish.py::test_non_workdir_is_refused PASSED                 [ 90%]
tests/test_finish.py::test_rebuild_clears_stale_figures PASSED           [100%]
======================== 10 passed, 5 warnings in 1.00s ========================
```

**Full suite before committing**

```
$ uv run pytest
86 passed, 5 warnings in 1.58s
```

76 pre-existing + 10 new = 86, matching the task's expected total.

## Files changed

- `src/lecnotes/commands.py` (modified — appended `finish`, extended the
  `.figures` import)
- `tests/test_finish.py` (new)

## Deviations from the brief

None. Implementation and test file match the brief's Step 1 and Step 3 code
verbatim.

## Self-review findings

- Read the diff fresh: `finish` follows the same shape and doc-comment style
  as `prep` (a short "why" comment on the validate-before-write ordering and
  the rebuild-clears-stale-figures `rmtree`). No dead code, no abstractions
  beyond what the brief specifies.
- Verified the dependency direction constraint from `global-constraints.md`
  still holds: `commands.py` imports only from `workdir`, `errors`, `figures`,
  `ingest`, `instructions`, `render`.
- Verified the two invariants called out in the dispatch message with
  dedicated tests, and traced them through the code:
  - Validation before writing: `body`/stub checks and the `bad_refs` check
    both run before `workdir.out_figures_dir` is touched or created, so a bad
    reference raises `figure_out_of_range` with `out/` never created
    (`test_nothing_is_written_when_validation_fails` asserts
    `not workdir.out_dir(prepared).exists()`).
  - Rebuild clears stale figures: `out/figures` is `rmtree`'d (if present)
    and recreated on every successful `finish` before cropping, so a second
    run with a different figure set leaves only the current run's PNGs
    (`test_rebuild_clears_stale_figures`).
- Confirmed error codes and exit codes match `global-constraints.md`:
  `not_a_workdir` → 1, `notes_empty` → 1, `figure_out_of_range` → 1 (all three
  fall through `LecnotesError.exit_code`'s default, since none is in
  `_DEPENDENCY_CODES`).
- Confirmed `bad_refs` ordering matches `find_refs`'s sorted, de-duplicated
  output (slide 7 before slide 91), which is what
  `test_every_bad_reference_is_reported_not_just_the_first` pins down.

## Concerns

None. `finish` is fully covered by its 10 tests and the full suite is green
at the expected 86.
