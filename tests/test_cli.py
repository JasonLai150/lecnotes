import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from lecnotes import commands, workdir
from lecnotes.cli import main


@pytest.fixture
def deck(synth, tmp_path):
    return synth(tmp_path / "lec1.pdf", [{"text": f"S{i}", "small_box": (100, 100, 300, 220)}
                                         for i in range(1, 6)])


def test_prep_succeeds_and_prints_next_step(deck, tmp_path, capsys):
    assert main(["prep", str(deck)]) == 0
    out = capsys.readouterr().out
    assert "lec1.notes" in out
    # The slide count line says only "N slides" -- nothing trails the newline.
    assert "  5 slides\n" in out
    assert "lecnotes finish" in out


def test_prep_json_is_parseable_and_complete(deck, capsys):
    assert main(["prep", str(deck), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["deck"] == "lec1"
    assert payload["slides"] == 5
    assert "figures" not in payload
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


def test_export_html_human_output(synth, tmp_path, capsys):
    root = _finished(synth, tmp_path)
    capsys.readouterr()
    assert main(["export", str(root), "--to", "html"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == str(root / "out" / "lec1.html")
    assert "1 image" in out


def test_export_notion_json(synth, tmp_path, capsys):
    root = _finished(synth, tmp_path)
    capsys.readouterr()
    assert main(["export", str(root), "--to", "notion", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["format"] == "notion"
    assert payload["output"].endswith("lec1-notion.zip")
    assert payload["images"] == 1 and payload["bytes"] > 0


def test_export_requires_to(tmp_path, capsys):
    md = tmp_path / "n.md"
    md.write_text("x\n")
    assert main(["export", str(md)]) == 1
    assert "--to" in capsys.readouterr().err


def test_export_rejects_unknown_format(tmp_path, capsys):
    md = tmp_path / "n.md"
    md.write_text("x\n")
    assert main(["export", str(md), "--to", "pdf"]) == 1


# --- every error code, in both output modes ---------------------------------
#
# Each scenario builds the situation on disk and returns the argv that trips it.


def _prepped(synth, tmp_path, notes=None):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": f"S{i}"} for i in range(1, 4)])
    root = tmp_path / "lec1.notes"
    commands.prep(pdf)
    if notes is not None:
        workdir.notes_path(root).write_text(notes)
    return pdf, root


def _source_not_found(tmp_path, synth, monkeypatch):
    return ["prep", str(tmp_path / "nope.pdf")]


def _unsupported_format(tmp_path, synth, monkeypatch):
    key = tmp_path / "lec1.key"
    key.write_bytes(b"stub")
    return ["prep", str(key)]


def _invalid_pdf(tmp_path, synth, monkeypatch):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf")
    return ["prep", str(broken)]


def _missing_converter(tmp_path, synth, monkeypatch):
    monkeypatch.setattr("lecnotes.ingest.shutil.which", lambda _: None)
    pptx = tmp_path / "lec1.pptx"
    pptx.write_bytes(b"stub")
    return ["prep", str(pptx)]


def _conversion_failed(tmp_path, synth, monkeypatch):
    monkeypatch.setattr("lecnotes.ingest.shutil.which", lambda _: "/usr/bin/soffice")
    monkeypatch.setattr(
        "lecnotes.ingest.subprocess.run",
        lambda *a, **k: SimpleNamespace(returncode=1, stdout=b"", stderr=b"soffice: boom\n"),
    )
    pptx = tmp_path / "lec1.pptx"
    pptx.write_bytes(b"stub")
    return ["prep", str(pptx)]


def _workdir_exists(tmp_path, synth, monkeypatch):
    pdf, _ = _prepped(synth, tmp_path)
    return ["prep", str(pdf)]


def _not_a_workdir(tmp_path, synth, monkeypatch):
    return ["finish", str(tmp_path)]


def _notes_empty(tmp_path, synth, monkeypatch):
    _, root = _prepped(synth, tmp_path)
    return ["finish", str(root)]


def _figure_out_of_range(tmp_path, synth, monkeypatch):
    _, root = _prepped(synth, tmp_path, notes="![x](figures/slide-091.png)\n")
    return ["finish", str(root)]


def _figure_malformed(tmp_path, synth, monkeypatch):
    _, root = _prepped(synth, tmp_path, notes="![x](pages/slide-002.png)\n")
    return ["finish", str(root)]


def _finished(synth, tmp_path, notes="# T\n\n![a](figures/slide-001.png)\n"):
    pdf, root = _prepped(synth, tmp_path, notes=notes)
    commands.finish(root)
    return root


def _not_finished(tmp_path, synth, monkeypatch):
    _, root = _prepped(synth, tmp_path)
    return ["export", str(root), "--to", "html"]


def _image_not_found(tmp_path, synth, monkeypatch):
    md = tmp_path / "notes.md"
    md.write_text("![x](figures/missing.png)\n")
    return ["export", str(md), "--to", "html"]


def _image_outside_root(tmp_path, synth, monkeypatch):
    from conftest import make_png

    make_png(tmp_path / "shared" / "x.png")
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "n.md").write_text("![x](../shared/x.png)\n")
    return ["export", str(notes / "n.md"), "--to", "notion"]


ERROR_SCENARIOS = {
    "source_not_found": (_source_not_found, 1),
    "unsupported_format": (_unsupported_format, 1),
    "invalid_pdf": (_invalid_pdf, 1),
    "missing_converter": (_missing_converter, 2),
    "conversion_failed": (_conversion_failed, 2),
    "workdir_exists": (_workdir_exists, 1),
    "not_a_workdir": (_not_a_workdir, 1),
    "notes_empty": (_notes_empty, 1),
    "figure_out_of_range": (_figure_out_of_range, 1),
    "figure_malformed": (_figure_malformed, 1),
    "not_finished": (_not_finished, 1),
    "image_not_found": (_image_not_found, 1),
    "image_outside_root": (_image_outside_root, 1),
}


def test_every_raised_error_code_has_a_cli_scenario():
    src = Path(__file__).resolve().parents[1] / "src" / "lecnotes"
    raised = {
        code
        for py in src.rglob("*.py")
        for code in re.findall(r'LecnotesError\(\s*"(\w+)"', py.read_text(encoding="utf-8"))
    }
    assert raised == set(ERROR_SCENARIOS)


@pytest.mark.parametrize("code", ERROR_SCENARIOS)
def test_error_code_in_json_mode(code, tmp_path, synth, monkeypatch, capsys):
    scenario, exit_code = ERROR_SCENARIOS[code]
    argv = scenario(tmp_path, synth, monkeypatch)
    capsys.readouterr()  # drop anything setup printed

    assert main([*argv, "--json"]) == exit_code
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"] == code
    assert isinstance(payload["message"], str) and payload["message"].strip()


@pytest.mark.parametrize("code", ERROR_SCENARIOS)
def test_error_code_in_human_mode(code, tmp_path, synth, monkeypatch, capsys):
    scenario, exit_code = ERROR_SCENARIOS[code]
    argv = scenario(tmp_path, synth, monkeypatch)
    capsys.readouterr()

    assert main(argv) == exit_code
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip()
