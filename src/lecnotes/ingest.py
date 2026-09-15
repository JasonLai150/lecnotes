"""Turn whatever the user handed us into a PDF we can render."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from .errors import LecnotesError
from .naming import slugify

CONVERTIBLE = {".pptx", ".ppt"}
STDERR_TAIL_LINES = 20  # enough to see why soffice failed, not its whole log
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
    proc = subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmpdir), str(path)],
        check=False,
        capture_output=True,
    )

    out = tmpdir / f"{path.stem}.pdf"
    if not out.is_file():
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace")
        raise LecnotesError(
            "conversion_failed",
            f"soffice ran but produced no PDF for {path.name}",
            source=str(path),
            stderr="\n".join(stderr.splitlines()[-STDERR_TAIL_LINES:]),
        )
    return out


def _check_pdf(pdf: Path, source: Path) -> None:
    """Refuse a PDF prep could not render, before anything is written to disk."""
    try:
        doc = pymupdf.open(pdf)
    except Exception as err:  # pymupdf raises several unrelated types for bad input
        raise LecnotesError(
            "invalid_pdf",
            f"{source.name} could not be opened as a PDF ({err})",
            path=str(source),
        ) from err
    try:
        if doc.needs_pass:
            problem = "is password-protected"
        elif doc.page_count < 1:
            problem = "has no pages"
        else:
            return
    finally:
        doc.close()
    raise LecnotesError("invalid_pdf", f"{source.name} {problem}", path=str(source))


def resolve_source(path: Path, tmpdir: Path) -> SourceInfo:
    """Return a PDF ready to render, converting from PowerPoint if needed."""
    path = Path(path)
    suffix = path.suffix.lower()

    if not path.is_file():
        raise LecnotesError("source_not_found", f"no such file: {path}", path=str(path))

    if suffix == ".key":
        raise LecnotesError(
            "unsupported_format",
            "Keynote files are not supported. In Keynote, use "
            "File > Export To > PDF, then pass the PDF.",
            suffix=suffix,
        )

    if suffix == ".pdf":
        pdf, converted = path, False
    elif suffix in CONVERTIBLE:
        pdf, converted = _convert(path, tmpdir), True
    else:
        raise LecnotesError(
            "unsupported_format",
            f"unsupported input {suffix or '(no extension)'}; expected .pdf, .pptx, or .ppt",
            suffix=suffix,
        )

    _check_pdf(pdf, path)

    return SourceInfo(
        pdf=pdf,
        deck=slugify(path.stem),
        source_name=path.name,
        source_format=suffix.lstrip("."),
        converted=converted,
    )
