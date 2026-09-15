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
