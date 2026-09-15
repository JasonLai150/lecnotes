import json
import shlex

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
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}, {"text": "b"}])
    prep(pdf)
    m = workdir.load_manifest(tmp_path / "lec1.notes")
    assert m["deck"] == "lec1"
    assert m["source"] == "lec1.pdf"
    assert m["source_format"] == "pdf"
    assert m["converted"] is False
    assert m["slides"] == 2
    assert m["rendered_long_edge"] == 1400
    assert len(m["pages"]) == 2
    assert "figures" not in m
    assert all(set(p.keys()) == {"n", "png", "txt", "chars"} for p in m["pages"])


def test_notes_starts_as_the_stub(synth, tmp_path):
    prep(synth(tmp_path / "lec1.pdf", [{"text": "a"}]))
    assert workdir.notes_path(tmp_path / "lec1.notes").read_text() == NOTES_STUB


def test_result_tells_the_agent_what_to_do_next(synth, tmp_path):
    result = prep(synth(tmp_path / "lec1.pdf", [{"text": "a"}]))
    assert result["ok"] is True
    assert result["write_to"].endswith("NOTES.md")
    assert result["instructions"].endswith("INSTRUCTIONS.md")
    assert result["next"] == f"lecnotes finish {shlex.quote(str(tmp_path / 'lec1.notes'))}"
    assert result["notes_preserved"] is False


def test_result_has_no_figures_key(synth, tmp_path):
    result = prep(synth(tmp_path / "lec1.pdf", [{"text": "a"}]))
    assert "figures" not in result


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
    stale = workdir.load_manifest(root) | {"slides": 99}
    workdir.save_manifest(root, stale)
    prep(pdf, force=True)
    assert workdir.load_manifest(root)["slides"] == 1


def test_force_refuses_a_directory_with_a_foreign_manifest(synth, tmp_path):
    """A web app's manifest.json must not pass for a workdir and cost it pages/."""
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}])
    app = tmp_path / "my-pwa"
    (app / "pages").mkdir(parents=True)
    (app / "pages" / "index.tsx").write_text("export default function Home() {}")
    (app / "manifest.json").write_text('{"name": "my pwa"}')
    before = sorted(str(p.relative_to(app)) for p in app.rglob("*"))

    with pytest.raises(LecnotesError) as exc:
        prep(pdf, out=app, force=True)

    assert exc.value.code == "workdir_exists"
    assert sorted(str(p.relative_to(app)) for p in app.rglob("*")) == before
    assert (app / "pages" / "index.tsx").read_text() == "export default function Home() {}"
    assert (app / "manifest.json").read_text() == '{"name": "my pwa"}'


def test_missing_source_leaves_nothing_behind(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        prep(tmp_path / "lec1.pdf")
    assert exc.value.code == "source_not_found"
    assert not (tmp_path / "lec1.notes").exists()


def test_corrupt_pdf_fails_before_creating_the_workdir(synth, tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf")
    root = tmp_path / "broken.notes"

    with pytest.raises(LecnotesError) as exc:
        prep(broken)
    assert exc.value.code == "invalid_pdf"
    assert not root.exists()

    # Nothing half-made is left in the way of a retry with a good file.
    synth(broken, [{"text": "fixed"}])
    assert prep(broken)["workdir"] == str(root)
    assert workdir.load_manifest(root)["slides"] == 1


def test_force_with_a_corrupt_pdf_leaves_the_existing_workdir_intact(synth, tmp_path):
    good = synth(tmp_path / "lec1.pdf", [{"text": "a"}, {"text": "b"}])
    root = tmp_path / "lec1.notes"
    prep(good)
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf")

    with pytest.raises(LecnotesError) as exc:
        prep(broken, out=root, force=True)

    assert exc.value.code == "invalid_pdf"
    assert workdir.page_png(root, 2).is_file()
    assert workdir.source_path(root).read_bytes() == good.read_bytes()


def test_force_from_the_workdirs_own_source_pdf(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}, {"text": "b"}])
    root = tmp_path / "lec1.notes"
    prep(pdf)
    own = workdir.source_path(root)

    result = prep(own, out=root, force=True)

    assert result["slides"] == 2
    assert own.read_bytes() == pdf.read_bytes()
    assert workdir.page_png(root, 2).is_file()


def test_next_command_quotes_a_workdir_path_with_spaces(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}])
    root = tmp_path / "Fall 2026" / "lec 1.notes"
    result = prep(pdf, out=root)
    assert result["next"] == f"lecnotes finish '{root}'"
    assert shlex.split(result["next"]) == ["lecnotes", "finish", str(root)]


def test_written_instructions_say_to_finish_from_inside_the_workdir(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}])
    root = tmp_path / "somewhere else"
    prep(pdf, out=root)
    text = workdir.instructions_path(root).read_text()
    assert "lecnotes finish .\n" in text
    assert "somewhere else" not in text
