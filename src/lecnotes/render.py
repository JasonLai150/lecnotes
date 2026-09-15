"""PDF to per-slide PNG plus per-slide text."""

from pathlib import Path

import pymupdf

from . import workdir
from .figures import TARGET_LONG_EDGE


def render_deck(pdf_path: Path, root: Path) -> list[dict]:
    """Render every page into the workdir; return the manifest rows."""
    doc = pymupdf.open(pdf_path)
    try:
        # Only once the document has opened, so a bad PDF leaves no pages/ behind.
        workdir.pages_dir(root).mkdir(parents=True, exist_ok=True)
        rows = []
        for i, page in enumerate(doc, start=1):
            zoom = TARGET_LONG_EDGE / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            pix.save(workdir.page_png(root, i))

            text = page.get_text().strip()
            workdir.page_txt(root, i).write_text(text, encoding="utf-8")

            rows.append(
                {
                    "n": i,
                    "png": workdir.rel_png(i),
                    "txt": workdir.rel_txt(i),
                    "chars": len(text),
                }
            )
        return rows
    finally:
        doc.close()
