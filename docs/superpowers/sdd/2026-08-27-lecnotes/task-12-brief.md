### Task 12: The CLI

**Files:**
- Create: `src/lecnotes/cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `commands.prep`, `commands.finish`, `errors.LecnotesError`, `lecnotes.__version__`
- Produces: `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
import json

import pytest

from lecnotes import workdir
from lecnotes.cli import main


@pytest.fixture
def deck(synth, tmp_path):
    return synth(tmp_path / "lec1.pdf", [{"text": f"S{i}", "small_box": (100, 100, 300, 220)}
                                         for i in range(1, 6)])


def test_prep_succeeds_and_prints_next_step(deck, tmp_path, capsys):
    assert main(["prep", str(deck)]) == 0
    out = capsys.readouterr().out
    assert "lec1.notes" in out
    assert "5 slides" in out
    assert "lecnotes finish" in out


def test_prep_json_is_parseable_and_complete(deck, capsys):
    assert main(["prep", str(deck), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["deck"] == "lec1"
    assert payload["slides"] == 5
    assert payload["notes_preserved"] is False
    assert payload["write_to"].endswith("NOTES.md")
    assert payload["next"].startswith("lecnotes finish")


def test_full_round_trip(deck, tmp_path, capsys):
    assert main(["prep", str(deck)]) == 0
    capsys.readouterr()  # discard prep's output so only finish's JSON is parsed
    root = tmp_path / "lec1.notes"
    workdir.notes_path(root).write_text("# Notes\n\n![n](figures/slide-002.png)\n")
    assert main(["finish", str(root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["figures_resolved"] == 1
    assert (root / "out" / "lec1.md").is_file()
    assert (root / "out" / "figures" / "slide-002.png").is_file()


def test_validation_failure_exits_1_with_json_error(deck, tmp_path, capsys):
    main(["prep", str(deck)])
    capsys.readouterr()  # discard prep's output so only finish's JSON is parsed
    root = tmp_path / "lec1.notes"
    workdir.notes_path(root).write_text("![x](figures/slide-091.png)\n")
    assert main(["finish", str(root), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": False,
        "error": "figure_out_of_range",
        "bad_refs": [{"slide": 91, "max": 5}],
    }


def test_errors_go_to_stderr_in_human_mode(deck, tmp_path, capsys):
    main(["prep", str(deck)])
    capsys.readouterr()  # discard prep's stdout; the assertion is about finish alone
    root = tmp_path / "lec1.notes"
    workdir.notes_path(root).write_text("![x](figures/slide-091.png)\n")
    assert main(["finish", str(root)]) == 1
    captured = capsys.readouterr()
    assert "91" in captured.err
    assert captured.out == ""


def test_missing_dependency_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("lecnotes.ingest.shutil.which", lambda _: None)
    pptx = tmp_path / "lec1.pptx"
    pptx.write_bytes(b"stub")
    assert main(["prep", str(pptx)]) == 2
    assert "libreoffice" in capsys.readouterr().err


def test_not_a_workdir_exits_1(tmp_path):
    assert main(["finish", str(tmp_path)]) == 1


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "0.1.0" in capsys.readouterr().out


def test_no_command_exits_nonzero(capsys):
    assert main([]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.cli'`

- [ ] **Step 3: Write minimal implementation**

Create `src/lecnotes/cli.py`:

```python
"""Argument parsing, output shaping, exit codes. Nothing else lives here."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .commands import finish, prep
from .errors import LecnotesError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lecnotes",
        description="Turn a lecture deck into a workdir an agent can write notes from.",
    )
    parser.add_argument("--version", action="version", version=f"lecnotes {__version__}")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("prep", help="render a deck into a new workdir")
    p.add_argument("source", type=Path, help="deck to prepare (.pdf, .pptx, .ppt)")
    p.add_argument("-o", "--out", type=Path, default=None, help="workdir path")
    p.add_argument("--force", action="store_true", help="re-render an existing workdir")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    f = sub.add_parser("finish", help="validate figure links and assemble the document")
    f.add_argument("workdir", type=Path, help="workdir created by prep")
    f.add_argument("--json", action="store_true", help="machine-readable output")

    return parser


def _report_prep(result: dict) -> None:
    print(f"{result['workdir']}")
    print(f"  {result['slides']} slides, {result['figures']} with figures")
    if result["notes_preserved"]:
        print("  NOTES.md preserved (not overwritten)")
    print(f"  read  {result['instructions']}")
    print(f"  write {result['write_to']}")
    print(f"  then  {result['next']}")


def _report_finish(result: dict) -> None:
    print(f"{result['output']}")
    print(f"  {result['figures_resolved']} figures resolved")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_usage(sys.stderr)
        return 1

    try:
        if args.command == "prep":
            result = prep(args.source, out=args.out, force=args.force)
            reporter = _report_prep
        else:
            result = finish(args.workdir)
            reporter = _report_finish
    except LecnotesError as err:
        # One place renders every failure, so --json and human output cannot drift.
        if args.json:
            print(json.dumps(err.to_dict()))
        else:
            print(f"error: {err.message}", file=sys.stderr)
        return err.exit_code

    if args.json:
        print(json.dumps(result))
    else:
        reporter(result)
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS, all tests across all files

- [ ] **Step 6: Commit**

```bash
git add src/lecnotes/cli.py tests/test_cli.py
git commit -m "Add the CLI"
```

---

