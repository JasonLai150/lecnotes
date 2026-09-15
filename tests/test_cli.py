import json
import subprocess
import sys

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
        "message": "NOTES.md references slides that are not in this deck: 91 (deck has 5)",
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


def test_unexpected_exception_in_json_mode_is_internal_error(deck, monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr("lecnotes.cli.prep", boom)
    assert main(["prep", str(deck), "--json"]) == 1
    assert json.loads(capsys.readouterr().out) == {
        "ok": False,
        "error": "internal_error",
        "message": "RuntimeError: disk on fire",
    }


def test_unexpected_exception_in_human_mode_propagates(deck, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr("lecnotes.cli.prep", boom)
    with pytest.raises(RuntimeError, match="disk on fire"):
        main(["prep", str(deck)])


@pytest.mark.parametrize("module", ["lecnotes", "lecnotes.cli"])
def test_runs_as_a_python_module(module):
    proc = subprocess.run(
        [sys.executable, "-m", module, "--version"], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr
    assert "lecnotes 0.1.0" in proc.stdout


def test_module_entry_point_propagates_the_exit_code(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "lecnotes", "finish", str(tmp_path), "--json"],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["error"] == "not_a_workdir"
