"""Markdown to a zip Notion's importer understands (Settings > Import > Markdown).

Notion resolves relative image links inside an imported zip, so the package is
just the Markdown plus its images at the same relative paths.
"""

import os
import re
import unicodedata
import zipfile
from pathlib import Path
from urllib.parse import unquote

from .markdown_doc import LocalImage
from .mdparse import PARSER

TITLE_MAX = 100
_WHITESPACE = re.compile(r"\s+")
_COLON = re.compile(r"\s*:\s*")
_UNSAFE_FILENAME_CHARS = re.compile(r'[/\\*?"<>|]')


def unwrap(markdown: str) -> str:
    """Join hard-wrapped paragraph lines.

    Notion merges wrapped lines into one paragraph but does not re-parse inline
    spans across the break, so `**bold**` split over two lines shows literal
    asterisks. Only paragraph line ranges are touched; code, tables, headings and
    blockquotes are left exactly as written.
    """
    lines = markdown.split("\n")
    ranges = []
    quote_depth = 0
    for token in PARSER.parse(markdown):
        if token.type == "blockquote_open":
            quote_depth += 1
        elif token.type == "blockquote_close":
            quote_depth -= 1
        elif (
            token.type == "paragraph_open"
            and quote_depth == 0
            and token.map
            and token.map[1] - token.map[0] > 1
        ):
            ranges.append(token.map)

    for start, end in reversed(ranges):
        joined = [lines[start]]
        for line in lines[start + 1 : end]:
            previous = joined[-1]
            if previous.endswith("  ") or previous.endswith("\\"):
                joined.append(line)  # a hard line break the author meant
            else:
                joined[-1] = previous.rstrip() + " " + line.strip()
        lines[start:end] = joined
    return "\n".join(lines)


def sanitize_filename(text: str) -> str:
    """A page title safe to use as a file name on every platform."""
    text = _WHITESPACE.sub(" ", text)  # also joins a setext heading's lines
    text = "".join(c for c in text if not unicodedata.category(c).startswith("C"))
    text = _COLON.sub(" - ", text)
    text = _UNSAFE_FILENAME_CHARS.sub("-", text)
    return text.strip()[:TITLE_MAX].strip()


def split_title(markdown: str, fallback_stem: str) -> tuple[str, str]:
    """Name the page after the first top-level H1, and drop that heading.

    Notion titles an imported page after its file name; keeping the heading too
    would show the title twice.
    """
    tokens = PARSER.parse(markdown)
    for i, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h1" and token.level == 0:
            text = PARSER.renderer.renderInlineAsText(
                tokens[i + 1].children or [], PARSER.options, {}
            )
            stem = sanitize_filename(text)
            if not stem or not token.map:
                return fallback_stem, markdown
            lines = markdown.split("\n")
            start, end = token.map
            del lines[start:end]
            return stem, "\n".join(lines).lstrip("\n")
    return fallback_stem, markdown


def images_outside(images: list[LocalImage], base_dir: Path) -> list[str]:
    """Srcs that are absolute or climb out of base_dir; a zip entry cannot mirror them.

    Judged on the link as written, because the zip stores each image at that
    name: that is what the Markdown inside the zip will look for.
    """
    outside = []
    for image in images:
        src = unquote(image.src)
        relpath = image.relpath
        if (
            os.path.isabs(src)
            or src.startswith("/")
            or relpath == ".."
            or relpath.startswith("../")
        ):
            outside.append(image.src)
    return outside


def write_notion_zip(
    markdown: str,
    images: list[LocalImage],
    base_dir: Path,
    dest: Path,
    fallback_stem: str,
) -> None:
    """Write the zip. Images must exist and not be outside base_dir (images_outside)."""
    stem, body = split_title(markdown, fallback_stem)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Each image is stored under the name the Markdown links to, so the link
    # resolves inside the zip even when the file on disk is a symlink. Two srcs
    # can name one entry (figures/x.png and ./figures/x.png).
    entries: dict[str, Path] = {}
    for image in images:
        entries.setdefault(image.relpath, image.path)

    tmp = dest.with_name(dest.name + ".tmp")
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{stem}.md", unwrap(body))
            for relpath, path in entries.items():
                zf.write(path, relpath)
        tmp.replace(dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
