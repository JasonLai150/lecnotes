import pytest

from lecnotes.errors import LecnotesError
from lecnotes.ingest import resolve_source


def test_pdf_passes_through(synth, tmp_path):
    pdf = synth(tmp_path / "lec1.pdf", [{"text": "a"}])
    info = resolve_source(pdf, tmp_path / "tmp")
    assert info.pdf == pdf
    assert info.deck == "lec1"
    assert info.source_name == "lec1.pdf"
    assert info.source_format == "pdf"
    assert info.converted is False


def test_deck_name_is_slugged(synth, tmp_path):
    pdf = synth(tmp_path / "lec8-txn,cc.pdf", [{"text": "a"}])
    assert resolve_source(pdf, tmp_path / "tmp").deck == "lec8-txn-cc"


def test_missing_file_is_a_usage_error(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        resolve_source(tmp_path / "nope.pdf", tmp_path / "tmp")
    assert exc.value.code == "unsupported_format"


def test_keynote_points_at_keynote_export(tmp_path):
    key = tmp_path / "lec1.key"
    key.write_bytes(b"stub")
    with pytest.raises(LecnotesError) as exc:
        resolve_source(key, tmp_path / "tmp")
    assert exc.value.code == "unsupported_format"
    assert exc.value.exit_code == 1
    assert "Keynote" in exc.value.message


def test_unknown_extension_is_rejected(tmp_path):
    odd = tmp_path / "lec1.txt"
    odd.write_text("stub")
    with pytest.raises(LecnotesError) as exc:
        resolve_source(odd, tmp_path / "tmp")
    assert exc.value.code == "unsupported_format"


def test_pptx_without_soffice_names_the_install_command(tmp_path, monkeypatch):
    monkeypatch.setattr("lecnotes.ingest.shutil.which", lambda _: None)
    pptx = tmp_path / "lec1.pptx"
    pptx.write_bytes(b"stub")
    with pytest.raises(LecnotesError) as exc:
        resolve_source(pptx, tmp_path / "tmp")
    assert exc.value.code == "missing_converter"
    assert exc.value.exit_code == 2
    assert "brew install --cask libreoffice" in exc.value.message


def test_pptx_conversion_that_emits_no_pdf_fails_clearly(tmp_path, monkeypatch, synth):
    monkeypatch.setattr("lecnotes.ingest.shutil.which", lambda _: "/usr/bin/soffice")
    monkeypatch.setattr("lecnotes.ingest.subprocess.run", lambda *a, **k: None)
    pptx = tmp_path / "lec1.pptx"
    pptx.write_bytes(b"stub")
    with pytest.raises(LecnotesError) as exc:
        resolve_source(pptx, tmp_path / "tmp")
    assert exc.value.code == "conversion_failed"
    assert exc.value.exit_code == 2


def test_pptx_conversion_success(tmp_path, monkeypatch, synth):
    tmpdir = tmp_path / "tmp"
    monkeypatch.setattr("lecnotes.ingest.shutil.which", lambda _: "/usr/bin/soffice")

    def fake_run(cmd, **kwargs):
        # soffice writes <stem>.pdf into the outdir; stand in for that.
        synth(tmpdir / "lec1.pdf", [{"text": "converted"}])

    monkeypatch.setattr("lecnotes.ingest.subprocess.run", fake_run)
    pptx = tmp_path / "lec1.pptx"
    pptx.write_bytes(b"stub")

    info = resolve_source(pptx, tmpdir)
    assert info.pdf == tmpdir / "lec1.pdf"
    assert info.converted is True
    assert info.source_format == "pptx"
    assert info.source_name == "lec1.pptx"
    assert info.deck == "lec1"
