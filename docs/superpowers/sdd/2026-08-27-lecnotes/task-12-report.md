# Task 12 report: The CLI

## What I implemented

- `src/lecnotes/cli.py` — argparse-based CLI exposing `main(argv: list[str] | None = None) -> int`, with `prep` and `finish` subcommands, `--version`, and `--json` on both subcommands. All `LecnotesError` failures are caught in one place and rendered either as `json.dumps(err.to_dict())` on stdout (`--json`) or `error: {message}` on stderr (human mode), returning `err.exit_code`. No command prints its usage to stderr and returns 1. Success renders either `json.dumps(result)` or a human-readable report via `_report_prep` / `_report_finish`.
- `tests/test_cli.py` — 9 tests covering: prep human output, prep `--json` payload shape, a full prep→finish round trip, a `finish --json` validation failure (`figure_out_of_range`), the same failure in human mode (message on stderr, stdout empty), a missing-LibreOffice dependency failure (exit 2), `finish` against a non-workdir (exit 1), `--version` (SystemExit 0), and no-subcommand (exit 1).

Implementation is verbatim from the brief's Step 3 code block; no changes were needed to satisfy it — `commands.prep`/`commands.finish`, `errors.LecnotesError`, `lecnotes.__version__`, and `tests/conftest.py`'s `synth` fixture all behaved exactly as the brief assumed.

## TDD evidence

**RED**

Command: `uv run pytest tests/test_cli.py -v`

Relevant output:
```
tests/test_cli.py:6: in <module>
    from lecnotes.cli import main
E   ModuleNotFoundError: No module named 'lecnotes.cli'
...
=========================== short test summary info ============================
ERROR tests/test_cli.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```
Expected failure reason per the brief (`ModuleNotFoundError: No module named 'lecnotes.cli'`) — confirmed.

**GREEN**

Command: `uv run pytest tests/test_cli.py -v`

Output:
```
tests/test_cli.py::test_prep_succeeds_and_prints_next_step PASSED        [ 11%]
tests/test_cli.py::test_prep_json_is_parseable_and_complete PASSED       [ 22%]
tests/test_cli.py::test_full_round_trip PASSED                           [ 33%]
tests/test_cli.py::test_validation_failure_exits_1_with_json_error PASSED [ 44%]
tests/test_cli.py::test_errors_go_to_stderr_in_human_mode PASSED         [ 55%]
tests/test_cli.py::test_missing_dependency_exits_2 PASSED                [ 66%]
tests/test_cli.py::test_not_a_workdir_exits_1 PASSED                     [ 77%]
tests/test_cli.py::test_version_flag PASSED                              [ 88%]
tests/test_cli.py::test_no_command_exits_nonzero PASSED                  [100%]
======================== 9 passed, 5 warnings in 0.55s =========================
```

**Full suite**

Command: `uv run pytest -v`

Output (tail):
```
======================== 95 passed, 5 warnings in 2.16s ========================
```
95 = 86 existing + 9 new, matching the expected total. The 5 warnings are pre-existing pymupdf `SwigPy*`/`swigvarlink` `DeprecationWarning`s unrelated to this task.

## Console script check

```
$ uv run lecnotes --help
usage: lecnotes [-h] [--version] {prep,finish} ...

Turn a lecture deck into a workdir an agent can write notes from.

positional arguments:
  {prep,finish}
    prep         render a deck into a new workdir
    finish       validate figure links and assemble the document

options:
  -h, --help     show this help message and exit
  --version      show program's version number and exit
EXIT:0

$ uv run lecnotes prep --help
usage: lecnotes prep [-h] [-o OUT] [--force] [--json] source

positional arguments:
  source             deck to prepare (.pdf, .pptx, .ppt)

options:
  -h, --help         show this help message and exit
  -o OUT, --out OUT  workdir path
  --force            re-render an existing workdir
  --json             machine-readable output
EXIT:0

$ uv run lecnotes finish --help
usage: lecnotes finish [-h] [--json] workdir

positional arguments:
  workdir     workdir created by prep

options:
  -h, --help  show this help message and exit
  --json      machine-readable output
EXIT:0
```

## Files changed

- `src/lecnotes/cli.py` (new)
- `tests/test_cli.py` (new)

## Deviations from the brief

None. Test file and implementation match the brief's code blocks verbatim, including the amendment (the three `finish`-related tests already call `capsys.readouterr()` right after `prep` to discard its stdout before exercising `finish`).

## Self-review

- Completeness: all 9 brief tests present and passing; `--help` sanity-checked for all three commands as instructed.
- Quality: `cli.py` does only argument parsing, output shaping, and exit codes, per the module's stated responsibility; no business logic leaked in.
- Discipline: no restructuring beyond this task; dependency direction (`cli` → `commands`/`errors`, nothing imports `cli`) preserved; no unused imports.
- Testing: tests exercise real `main()` behavior end-to-end (subprocess-free, via `capsys`), not mocks of the CLI's own internals.

## Concerns

None.

---

## Fix report: round 1 (review finding)

### Finding

`src/lecnotes/cli.py:66-72`: argparse's default error handling for a missing required positional argument or an unrecognized subcommand calls `sys.exit(2)` internally, bypassing `main()`'s normal return path entirely. This violated the exit-code contract (`1` usage or validation failure, `2` missing external dependency) and the interface contract (`main(argv) -> int`). Verified before the fix: `main(['prep'])`, `main(['finish'])`, `main(['bogus'])` all raised `SystemExit` code 2 (should return 1).

### What changed

`src/lecnotes/cli.py`:
- Added `_UsageError(Exception)`, a private exception.
- Added `_ArgumentParser(argparse.ArgumentParser)` overriding `error(message)` to print usage + the error line to stderr itself (replicating argparse's own formatting) and then raise `_UsageError` instead of calling `self.exit(2, ...)` (which is what triggers `sys.exit`).
- `_build_parser()` now builds the top-level parser as `_ArgumentParser` and passes `parser_class=_ArgumentParser` to `add_subparsers(...)`, so the `prep` and `finish` subparsers (created via `sub.add_parser(...)`) raise the same private exception on their own usage errors (e.g. missing `source`/`workdir`).
- `main()` now wraps `parser.parse_args(argv)` in `try/except _UsageError: return 1` (the usage/error text is already on stderr by the time `error()` raises, so no re-printing is needed).

`--help` and `--version` are unaffected: both use argparse's `_HelpAction`/`_VersionAction`, which call `parser.exit()` directly (not `error()`), so they still raise `SystemExit(0)` exactly as before — `test_version_flag` (which catches `SystemExit` with code 0) was left unchanged and still passes.

cli.py's scope is unchanged: still only argument parsing, output shaping, and exit codes.

### Covering tests added (tests/test_cli.py)

```python
def test_prep_missing_source_returns_1(capsys):
    assert main(["prep"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "source" in captured.err


def test_finish_missing_workdir_returns_1(capsys):
    assert main(["finish"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "workdir" in captured.err


def test_unknown_subcommand_returns_1(capsys):
    assert main(["bogus"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err != ""
```

### RED

Command: `uv run pytest tests/test_cli.py -v -k "missing_source or missing_workdir or unknown_subcommand"`

Relevant output (before the fix):
```
E       SystemExit: 2
----------------------------- Captured stderr call -----------------------------
usage: lecnotes [-h] [--version] {prep,finish} ...
lecnotes: error: argument command: invalid choice: 'bogus' (choose from 'prep', 'finish')
...
FAILED tests/test_cli.py::test_prep_missing_source_returns_1 - SystemExit: 2
FAILED tests/test_cli.py::test_finish_missing_workdir_returns_1 - SystemExit: 2
FAILED tests/test_cli.py::test_unknown_subcommand_returns_1 - SystemExit: 2
3 failed, 9 deselected, 5 warnings in 0.20s
```
All three failed for the expected reason: `SystemExit(2)` escaping `main()` instead of a `1` return value.

### GREEN

Command: `uv run pytest tests/test_cli.py -v`

Output:
```
tests/test_cli.py::test_prep_succeeds_and_prints_next_step PASSED        [  8%]
tests/test_cli.py::test_prep_json_is_parseable_and_complete PASSED       [ 16%]
tests/test_cli.py::test_full_round_trip PASSED                           [ 25%]
tests/test_cli.py::test_validation_failure_exits_1_with_json_error PASSED [ 33%]
tests/test_cli.py::test_errors_go_to_stderr_in_human_mode PASSED         [ 41%]
tests/test_cli.py::test_missing_dependency_exits_2 PASSED                [ 50%]
tests/test_cli.py::test_not_a_workdir_exits_1 PASSED                     [ 58%]
tests/test_cli.py::test_version_flag PASSED                              [ 66%]
tests/test_cli.py::test_no_command_exits_nonzero PASSED                  [ 75%]
tests/test_cli.py::test_prep_missing_source_returns_1 PASSED             [ 83%]
tests/test_cli.py::test_finish_missing_workdir_returns_1 PASSED          [ 91%]
tests/test_cli.py::test_unknown_subcommand_returns_1 PASSED              [100%]
======================== 12 passed, 5 warnings in 0.53s =========================
```

### Full suite

Command: `uv run pytest -q`

Output (tail):
```
98 passed, 5 warnings in 2.09s
```
98 = 95 previous + 3 new. The 5 warnings are the same pre-existing pymupdf `SwigPy*`/`swigvarlink` `DeprecationWarning`s, unrelated to this change.

### Console script re-check

```
$ uv run lecnotes --help    ; echo $?     -> exit 0
$ uv run lecnotes --version ; echo $?     -> exit 0
$ uv run lecnotes prep      ; echo $?     -> exit 1 (was 2)
$ uv run lecnotes finish    ; echo $?     -> exit 1 (was 2)
$ uv run lecnotes bogus     ; echo $?     -> exit 1 (was 2)
```

### Commit

`c15c6e1` "Fix CLI usage errors to return 1 instead of raising SystemExit(2)" — files changed: `src/lecnotes/cli.py`, `tests/test_cli.py`.

### Concerns

None.
