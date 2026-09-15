# Task 10 report: the `prep` command

## What was implemented

- `src/lecnotes/commands.py` — the orchestration module. `NOTES_STUB` (the
  literal stub text written into a fresh `NOTES.md`) and `prep(source, out=None,
  force=False) -> dict`, which:
  1. Resolves the source (PDF or converted PPTX) via `ingest.resolve_source`
     inside a `TemporaryDirectory`, so a converted PPTX's temp PDF is only ever
     read while the temp dir is alive.
  2. Computes the workdir root: `out` if given, else
     `<source's parent>/<slug>.notes`.
  3. Refuses to proceed (`workdir_exists`, exit 1) if the root already exists
     and `--force` wasn't passed.
  4. If `--force` was passed and the root exists but is **not** a lecnotes
     workdir (no `manifest.json`), refuses with the same `workdir_exists` code
     rather than deleting anything inside it. This is the safety guard added to
     the brief: `--force` re-renders `pages/` via `shutil.rmtree`, so it must
     never run against an arbitrary directory.
  5. Records whether `NOTES.md` already exists (`preserved`) *before* touching
     anything, deletes stale `pages/` (if present) so a shorter re-render
     can't leave orphaned page files, then calls `render.render_deck` and
     copies the source PDF into the workdir — both still inside the temp-dir
     block.
  6. After the temp dir closes, builds and saves `manifest.json`, renders and
     writes `INSTRUCTIONS.md`, and writes `NOTES.md` **only if it didn't
     already exist** — this is what makes `NOTES.md` un-clobberable by `prep`,
     with or without `--force`.
  7. Returns the result dict the brief specifies: `ok`, `workdir`, `deck`,
     `slides`, `figures`, `notes_preserved`, `instructions`, `write_to`, `next`.

- `tests/test_prep.py` — 12 tests, created verbatim from the brief's Step 1,
  covering: workdir naming (including slug derivation), that every workdir
  file gets written, that the source PDF is byte-identical once copied, the
  manifest's shape, the `NOTES.md` stub on first prep, the `next`/`write_to`
  hints returned to the agent, a custom `--out` directory, refusing an
  existing workdir without `--force`, that `--force` never clobbers
  hand-written `NOTES.md`, that `--force` refuses a non-workdir directory
  (the dedicated safety-guard test), and that `--force` does re-render
  everything else (manifest included).

## TDD evidence

**RED**

```
$ uv run pytest tests/test_prep.py -v
...
ImportError while importing test module '.../tests/test_prep.py'.
tests/test_prep.py:6: in <module>
    from lecnotes.commands import NOTES_STUB, prep
E   ModuleNotFoundError: No module named 'lecnotes.commands'
...
========================= 5 warnings, 1 error in 0.06s =========================
```

Expected failure reason, matches the brief's Step 2 exactly — `commands.py`
didn't exist yet.

**GREEN**

```
$ uv run pytest tests/test_prep.py -v
tests/test_prep.py::test_creates_workdir_named_after_the_deck PASSED     [  8%]
tests/test_prep.py::test_workdir_name_uses_the_slug PASSED               [ 16%]
tests/test_prep.py::test_writes_every_workdir_file PASSED                [ 25%]
tests/test_prep.py::test_source_pdf_is_copied_in PASSED                  [ 33%]
tests/test_prep.py::test_manifest_shape PASSED                           [ 41%]
tests/test_prep.py::test_notes_starts_as_the_stub PASSED                 [ 50%]
tests/test_prep.py::test_result_tells_the_agent_what_to_do_next PASSED   [ 58%]
tests/test_prep.py::test_custom_output_directory PASSED                  [ 66%]
tests/test_prep.py::test_existing_workdir_is_refused PASSED              [ 75%]
tests/test_prep.py::test_force_never_clobbers_written_notes PASSED       [ 83%]
tests/test_prep.py::test_force_refuses_a_directory_that_is_not_a_workdir PASSED [ 91%]
tests/test_prep.py::test_force_re_renders_the_rest PASSED                [100%]
======================== 12 passed, 5 warnings in 0.38s ========================
```

**Full suite before committing**

```
$ uv run pytest
======================== 76 passed, 5 warnings in 0.65s ========================
```

64 pre-existing + 12 new = 76, matching the task's expected total.

## Files changed

- `src/lecnotes/commands.py` (new)
- `tests/test_prep.py` (new)

## Deviations from the brief

None. Implementation and test file match the brief's Step 1 and Step 3 code
verbatim, including the amended `--force`-on-non-workdir safety guard and its
dedicated test.

## Self-review findings

- Read the diff fresh: naming is clear, the module docstring and inline
  comments match the existing codebase's style (explaining *why*, e.g. why
  `pages/` is read inside the temp-dir block, why stale `pages/` is dropped
  before re-rendering). No dead code, no extra abstractions beyond what the
  brief specifies.
- Verified the dependency direction constraint from `global-constraints.md`
  holds: `commands.py` imports only from `workdir`, `errors`, `figures`,
  `ingest`, `instructions`, `render` — nothing imports `cli` (which doesn't
  exist yet).
- Verified the two safety invariants explicitly called out by the dispatch
  message with dedicated tests:
  - `NOTES.md` is never overwritten by `prep`, with or without `--force`
    (`test_notes_starts_as_the_stub`, `test_force_never_clobbers_written_notes`).
  - `--force` refuses a target that exists but isn't a lecnotes workdir,
    rather than `rmtree`-ing into it (`test_force_refuses_a_directory_that_is_not_a_workdir`),
    and confirmed the file inside the unrelated directory survives the
    refused call.
- Minor observation (not changed): `tests/test_prep.py` imports `json` at the
  top but never uses it — carried over verbatim from the brief's exact Step 1
  test code, which the instructions treat as the literal source of truth.
  Purely cosmetic (no linter is configured in this project), so left as-is
  rather than deviating from the verbatim brief content.

## Concerns

None. `prep` is fully covered by its 12 tests and the full suite is green at
the expected 76.
