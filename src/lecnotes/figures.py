"""Content-box detection and cropped figure rendering."""

import re
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


# Exactly the form INSTRUCTIONS.md tells the agent to write. A workdir holds one
# deck, so there is no deck path segment. The number is written the way finish
# names the file it crops (`slide-{n:03d}.png`): three digits, or more without a
# leading zero, so `slide-1000.png` resolves and `slide-0001.png` cannot dangle.
REF_RE = re.compile(r"!\[([^\]]*)\]\(figures/slide-(\d{3}|[1-9]\d{3,})\.png\)")

# Any Markdown image, capturing its target. Used to catch slide links that are
# close to REF_RE but not it, which would otherwise pass silently as broken images.
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]*)\)")
SLIDE_PNG_RE = re.compile(r"slide-\d+\.png")


def find_refs(markdown: str) -> list[int]:
    """Sorted, de-duplicated slide numbers referenced as figures."""
    return sorted({int(n) for _, n in REF_RE.findall(markdown)})


def find_malformed(markdown: str) -> list[str]:
    """Targets of slide image links not in the exact reference form.

    In document order, de-duplicated.
    """
    bad: dict[str, None] = {}
    for m in IMAGE_RE.finditer(markdown):
        target = m.group(1)
        if SLIDE_PNG_RE.search(target) and not REF_RE.fullmatch(m.group(0)):
            bad.setdefault(target)
    return list(bad)
