import json

import pytest

from lecnotes import workdir
from lecnotes.commands import NOTES_STUB, prep
from lecnotes.errors import LecnotesError


def test_creates_workdir_named_after_the_deck(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}, {"text": "b"}])
    result = prep(pdf)
    assert result["workdir"] == str(tmp_path / "lec1.notes")
    assert (tmp_path / "lec1.notes").is_dir()


def test_workdir_name_uses_the_slug(synth, tmp_path):
    pdf = synth(tmp_path / "lec8-txn,cc.pdf", [{"text": "a"}])
    assert prep(pdf)["deck"] == "lec8-txn-cc"
    assert (tmp_path / "lec8-txn-cc.notes").is_dir()


def test_writes_every_workdir_file(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}, {"text": "b"}])
    root = tmp_path / "lec1.notes"
    prep(pdf)
    assert workdir.manifest_path(root).is_file()
    assert workdir.instructions_path(root).is_file()
    assert workdir.notes_path(root).is_file()
    assert workdir.source_path(root).is_file()
    assert workdir.page_png(root, 1).is_file()
    assert workdir.page_txt(root, 2).is_file()


def test_source_pdf_is_copied_in(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}])
    prep(pdf)
    copied = workdir.source_path(tmp_path / "lec1.notes")
    assert copied.read_bytes() == pdf.read_bytes()


def test_manifest_shape(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}, {"text": "b", "many_lines": 20}])
    prep(pdf)
    m = workdir.load_manifest(tmp_path / "lec1.notes")
    assert m["deck"] == "lec1"
    assert m["source"] == "lec1.pdf"
    assert m["source_format"] == "pdf"
    assert m["converted"] is False
    assert m["slides"] == 2
    assert m["figures"] == 1
    assert m["rendered_long_edge"] == 1400
    assert len(m["pages"]) == 2


def test_notes_starts_as_the_stub(synth, tmp_path):
    prep(synth(tmp_path / "lec1.pdf", [{"text": "a"}]))
    assert workdir.notes_path(tmp_path / "lec1.notes").read_text() == NOTES_STUB


def test_result_tells_the_agent_what_to_do_next(synth, tmp_path):
    result = prep(synth(tmp_path / "lec1.pdf", [{"text": "a"}]))
    assert result["ok"] is True
    assert result["write_to"].endswith("NOTES.md")
    assert result["instructions"].endswith("INSTRUCTIONS.md")
    assert result["next"] == f"lecnotes finish {tmp_path / 'lec1.notes'}"
    assert result["notes_preserved"] is False


def test_custom_output_directory(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}])
    result = prep(pdf, out=tmp_path / "elsewhere")
    assert result["workdir"] == str(tmp_path / "elsewhere")
    assert (tmp_path / "elsewhere" / "manifest.json").is_file()


def test_existing_workdir_is_refused(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}])
    prep(pdf)
    with pytest.raises(LecnotesError) as exc:
        prep(pdf)
    assert exc.value.code == "workdir_exists"
    assert exc.value.exit_code == 1


def test_force_never_clobbers_written_notes(synth, tmp_path):
    """The one behavior that must not regress: re-prepping cannot cost you writing."""
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}])
    prep(pdf)
    notes = workdir.notes_path(tmp_path / "lec1.notes")
    notes.write_text("# My hard-won notes\n")

    result = prep(pdf, force=True)

    assert notes.read_text() == "# My hard-won notes\n"
    assert result["notes_preserved"] is True


def test_force_refuses_a_directory_that_is_not_a_workdir(synth, tmp_path):
    """--force re-renders a workdir; it must never rmtree inside an arbitrary folder."""
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}])
    unrelated = tmp_path / "my-documents"
    (unrelated / "pages").mkdir(parents=True)
    (unrelated / "pages" / "precious.txt").write_text("keep me")
    with pytest.raises(LecnotesError) as exc:
        prep(pdf, out=unrelated, force=True)
    assert exc.value.code == "workdir_exists"
    assert (unrelated / "pages" / "precious.txt").read_text() == "keep me"


def test_force_re_renders_the_rest(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}])
    prep(pdf)
    root = tmp_path / "lec1.notes"
    workdir.manifest_path(root).write_text("{}")
    prep(pdf, force=True)
    assert workdir.load_manifest(root)["slides"] == 1
