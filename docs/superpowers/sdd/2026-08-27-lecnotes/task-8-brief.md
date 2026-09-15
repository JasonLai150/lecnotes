### Task 8: Input ingest and PPTX conversion

**Files:**
- Create: `src/lecnotes/ingest.py`
- Create: `tests/test_ingest.py`

**Interfaces:**
- Consumes: `lecnotes.errors.LecnotesError`, `lecnotes.naming.slugify`
- Produces:
  - `SourceInfo` — a `dataclass` with fields `pdf: Path`, `deck: str`, `source_name: str`, `source_format: str`, `converted: bool`
  - `resolve_source(path: Path, tmpdir: Path) -> SourceInfo` — returns a PDF ready to render, converting `.pptx`/`.ppt` into `tmpdir` when needed

- [ ] **Step 1: Write the failing test**

Create `tests/test_ingest.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.ingest'`

- [ ] **Step 3: Write minimal implementation**

Create `src/lecnotes/ingest.py`:

```python
"""Turn whatever the user handed us into a PDF we can render."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import LecnotesError
from .naming import slugify

CONVERTIBLE = {".pptx", ".ppt"}
INSTALL_HINT = (
    "Converting .pptx/.ppt needs LibreOffice:\n"
    "  brew install --cask libreoffice\n"
    "Or export the deck to PDF yourself and pass that instead."
)


@dataclass
class SourceInfo:
    pdf: Path
    deck: str
    source_name: str
    source_format: str
    converted: bool


def _convert(path: Path, tmpdir: Path) -> Path:
    if shutil.which("soffice") is None:
        raise LecnotesError("missing_converter", INSTALL_HINT, suffix=path.suffix)

    tmpdir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmpdir), str(path)],
        check=False,
        capture_output=True,
    )

    out = tmpdir / f"{path.stem}.pdf"
    if not out.is_file():
        raise LecnotesError(
            "conversion_failed",
            f"soffice ran but produced no PDF for {path.name}",
            source=str(path),
        )
    return out


def resolve_source(path: Path, tmpdir: Path) -> SourceInfo:
    """Return a PDF ready to render, converting from PowerPoint if needed."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".key":
        raise LecnotesError(
            "unsupported_format",
            "Keynote files are not supported. In Keynote, use "
            "File > Export To > PDF, then pass the PDF.",
            suffix=suffix,
        )

    if suffix == ".pdf":
        if not path.is_file():
            raise LecnotesError("unsupported_format", f"no such file: {path}", path=str(path))
        pdf, converted = path, False
    elif suffix in CONVERTIBLE:
        if not path.is_file():
            raise LecnotesError("unsupported_format", f"no such file: {path}", path=str(path))
        pdf, converted = _convert(path, tmpdir), True
    else:
        raise LecnotesError(
            "unsupported_format",
            f"unsupported input {suffix or '(no extension)'}; expected .pdf, .pptx, or .ppt",
            suffix=suffix,
        )

    return SourceInfo(
        pdf=pdf,
        deck=slugify(path.stem),
        source_name=path.name,
        source_format=suffix.lstrip("."),
        converted=converted,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ingest.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/ingest.py tests/test_ingest.py
git commit -m "Add input ingest with PPTX conversion"
```

---

