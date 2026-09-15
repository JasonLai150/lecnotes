"""Content-box detection and cropped figure rendering."""

from pathlib import Path

import pymupdf

PAD = 10  # points of breathing room around the content box
BACKDROP_RATIO = 0.95
TARGET_LONG_EDGE = 1400


def content_box(page: pymupdf.Page) -> pymupdf.Rect:
    """Union of everything drawn on the page, clipped to the page itself.

    Slide exports paint a full-page white rectangle behind every slide. Counting
    it would make the content box the whole page and defeat the crop, so anything
    covering nearly the entire page is treated as backdrop rather than content.
    """
    page_area = page.rect.get_area()

    def backdrop(rect: pymupdf.Rect) -> bool:
        return rect.get_area() >= BACKDROP_RATIO * page_area

    box = pymupdf.Rect()
    for block in page.get_text("blocks"):
        box |= pymupdf.Rect(block[:4])
    for img in page.get_image_info():
        rect = pymupdf.Rect(img["bbox"])
        if not backdrop(rect):
            box |= rect
    for drawing in page.get_drawings():
        if not backdrop(drawing["rect"]):
            box |= drawing["rect"]

    if box.is_empty:
        return page.rect
    box += (-PAD, -PAD, PAD, PAD)
    return box & page.rect


def crop_render(pdf_path: Path, slide: int, dest: Path) -> None:
    """Render one 1-indexed slide, cropped to its content box, to `dest`.

    Re-rendering from the PDF rather than cropping the page PNG means the crop
    gets the full 1400px long edge to itself, which is what makes small diagram
    labels legible.
    """
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[slide - 1]
        clip = content_box(page)
        zoom = TARGET_LONG_EDGE / max(clip.width, clip.height)
        dest.parent.mkdir(parents=True, exist_ok=True)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip)
        # get_pixmap rounds the transformed clip rect outward to whole pixels
        # (floor the top-left, ceil the bottom-right), which can land the long
        # edge one pixel past TARGET_LONG_EDGE even when `zoom` was chosen to
        # hit it exactly. Rescale onto the exact target so callers get a
        # consistent long edge.
        long_edge = max(pix.width, pix.height)
        if long_edge != TARGET_LONG_EDGE:
            fit = TARGET_LONG_EDGE / long_edge
            pix = pymupdf.Pixmap(pix, round(pix.width * fit), round(pix.height * fit))
        pix.save(dest)
    finally:
        doc.close()
