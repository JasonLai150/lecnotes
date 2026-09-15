"""PDF to per-slide PNG plus per-slide text."""

from pathlib import Path

import pymupdf

from . import workdir
from .figures import TARGET_LONG_EDGE

FIGURE_IMAGE_AREA = 40_000
FIGURE_DRAWING_COUNT = 12


def has_figure(page: pymupdf.Page) -> bool:
    """Whether this page carries something worth looking at rather than reading.

    A hint telling the agent where to look hard — nothing is withheld based on it.
    """
    big_images = [im for im in page.get_images(full=True) if im[2] * im[3] > FIGURE_IMAGE_AREA]
    return bool(big_images) or len(page.get_drawings()) > FIGURE_DRAWING_COUNT


def render_deck(pdf_path: Path, root: Path) -> list[dict]:
    """Render every page into the workdir; return the manifest rows."""
    workdir.pages_dir(root).mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    try:
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
                    "figure": has_figure(page),
                }
            )
        return rows
    finally:
        doc.close()
