from types import SimpleNamespace

import pymupdf
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


ZERO_PAGE_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
)


@pytest.mark.parametrize("name", ["nope.pdf", "nope.pptx", "nope.ppt"])
def test_missing_file_is_source_not_found(tmp_path, name):
    with pytest.raises(LecnotesError) as exc:
        resolve_source(tmp_path / name, tmp_path / "tmp")
    assert exc.value.code == "source_not_found"
    assert exc.value.exit_code == 1
    assert exc.value.detail["path"] == str(tmp_path / name)


def test_corrupt_pdf_is_invalid_pdf(tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf")
    with pytest.raises(LecnotesError) as exc:
        resolve_source(broken, tmp_path / "tmp")
    assert exc.value.code == "invalid_pdf"
    assert exc.value.exit_code == 1


def test_zero_page_pdf_is_invalid_pdf(tmp_path):
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(ZERO_PAGE_PDF)
    with pytest.raises(LecnotesError) as exc:
        resolve_source(empty, tmp_path / "tmp")
    assert exc.value.code == "invalid_pdf"


def test_password_protected_pdf_is_invalid_pdf(tmp_path):
    locked = tmp_path / "locked.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(locked, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o")
    doc.close()
    with pytest.raises(LecnotesError) as exc:
        resolve_source(locked, tmp_path / "tmp")
    assert exc.value.code == "invalid_pdf"


def test_converted_pdf_that_will_not_open_is_invalid_pdf(tmp_path, monkeypatch):
    tmpdir = tmp_path / "tmp"
    monkeypatch.setattr("lecnotes.ingest.shutil.which", lambda _: "/usr/bin/soffice")

    def fake_run(cmd, **kwargs):
        (tmpdir / "lec1.pdf").write_bytes(b"truncated garbage")
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr("lecnotes.ingest.subprocess.run", fake_run)
    pptx = tmp_path / "lec1.pptx"
    pptx.write_bytes(b"stub")
    with pytest.raises(LecnotesError) as exc:
        resolve_source(pptx, tmpdir)
    assert exc.value.code == "invalid_pdf"


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
    monkeypatch.setattr(
        "lecnotes.ingest.subprocess.run",
        lambda *a, **k: SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"Error: source file could not be loaded\n"
        ),
    )
    pptx = tmp_path / "lec1.pptx"
    pptx.write_bytes(b"stub")
    with pytest.raises(LecnotesError) as exc:
        resolve_source(pptx, tmp_path / "tmp")
    assert exc.value.code == "conversion_failed"
    assert exc.value.exit_code == 2
    assert "source file could not be loaded" in exc.value.detail["stderr"]


def test_conversion_failed_keeps_only_the_tail_of_stderr(tmp_path, monkeypatch):
    monkeypatch.setattr("lecnotes.ingest.shutil.which", lambda _: "/usr/bin/soffice")
    noisy = "".join(f"line {i}\n" for i in range(1, 101)).encode() + b"bad \xff byte\n"
    monkeypatch.setattr(
        "lecnotes.ingest.subprocess.run",
        lambda *a, **k: SimpleNamespace(returncode=1, stdout=b"", stderr=noisy),
    )
    pptx = tmp_path / "lec1.pptx"
    pptx.write_bytes(b"stub")
    with pytest.raises(LecnotesError) as exc:
        resolve_source(pptx, tmp_path / "tmp")
    lines = exc.value.detail["stderr"].splitlines()
    assert len(lines) == 20
    assert lines[0] == "line 82"
    assert lines[-1] == "bad \ufffd byte"


def test_pptx_conversion_success(tmp_path, monkeypatch, synth):
    tmpdir = tmp_path / "tmp"
    monkeypatch.setattr("lecnotes.ingest.shutil.which", lambda _: "/usr/bin/soffice")

    def fake_run(cmd, **kwargs):
        # soffice writes <stem>.pdf into the outdir; stand in for that.
        synth(tmpdir / "lec1.pdf", [{"text": "converted"}])
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr("lecnotes.ingest.subprocess.run", fake_run)
    pptx = tmp_path / "lec1.pptx"
    pptx.write_bytes(b"stub")

    info = resolve_source(pptx, tmpdir)
    assert info.pdf == tmpdir / "lec1.pdf"
    assert info.converted is True
    assert info.source_format == "pptx"
    assert info.source_name == "lec1.pptx"
    assert info.deck == "lec1"
