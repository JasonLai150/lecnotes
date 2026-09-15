"""Content-box detection and cropped figure rendering."""

import re
from collections.abc import Iterator
from pathlib import Path

import pymupdf
from markdown_it import MarkdownIt
from markdown_it.token import Token

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
STRICT_SRC_RE = re.compile(r"figures/slide-(\d{3}|[1-9]\d{3,})\.png")

# Looser: any string that merely looks like a slide image target, used to spot
# links that are close to STRICT_SRC_RE but not it, so they are reported rather
# than silently ignored.
SLIDE_PNG_RE = re.compile(r"slide-\d+\.png")

# Matches a `slide-NNN.png`-shaped run of non-whitespace, for pulling the
# offending fragment out of prose or markup that failed to parse as a link at
# all (an unclosed bracket, a bare filename mentioned in text, etc).
LOOSE_TEXT_RE = re.compile(r"\S*slide-\d+\.png\S*")

# One shared parser instance: markdown-it instances are stateful during parsing
# but safe to reuse across calls, and this is what the export feature can reuse
# later too.
_MD = MarkdownIt("commonmark", {"html": False})


def _iter_link_tokens(markdown: str) -> Iterator[Token]:
    """Yield inline `image`, `link_open`, and `text` tokens, in document order.

    These are the only token types that can carry a slide figure reference (or
    the text of one that failed to parse as a link). `code_inline`, `fence`,
    and `code_block` tokens are never yielded, so example links inside inline
    code or fenced code blocks are not treated as figure references.
    """
    for block in _MD.parse(markdown):
        if block.type != "inline" or not block.children:
            continue
        for token in block.children:
            if token.type in ("image", "link_open", "text"):
                yield token


def find_refs(markdown: str) -> list[int]:
    """Sorted, de-duplicated slide numbers referenced as figures."""
    nums: set[int] = set()
    for token in _iter_link_tokens(markdown):
        if token.type != "image":
            continue
        src = token.attrGet("src") or ""
        match = STRICT_SRC_RE.fullmatch(src)
        if match:
            nums.add(int(match.group(1)))
    return sorted(nums)


def find_malformed(markdown: str) -> list[str]:
    """Slide image links not in the exact reference form.

    In document order, de-duplicated. Covers three ways a link can be close to
    a valid figure reference without being one: an image whose src is not
    exactly `figures/slide-NNN.png` (wrong directory, `./` prefix, wrong
    padding, ...); a link missing its leading `!` (so it parses as a plain
    link, not an image); and markup that failed to parse as a link at all
    (an unbalanced `[` or `]` in the caption leaves raw `![...` text behind).
    """
    bad: dict[str, None] = {}
    for token in _iter_link_tokens(markdown):
        if token.type == "image":
            src = token.attrGet("src") or ""
            if SLIDE_PNG_RE.search(src) and not STRICT_SRC_RE.fullmatch(src):
                bad.setdefault(src)
        elif token.type == "link_open":
            href = token.attrGet("href") or ""
            if SLIDE_PNG_RE.search(href):
                bad.setdefault(href)
        elif token.type == "text":
            for m in LOOSE_TEXT_RE.finditer(token.content):
                bad.setdefault(m.group(0))
    return list(bad)
