"""Markdown to a zip Notion's importer understands (Settings > Import > Markdown).

Notion resolves relative image links inside an imported zip, so the package is
just the Markdown plus its images at the same relative paths.
"""

import re
import zipfile
from pathlib import Path

from .markdown_doc import LocalImage
from .mdparse import PARSER

TITLE_MAX = 100
_UNSAFE_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|]')


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
    return _UNSAFE_FILENAME_CHARS.sub("-", text).strip()[:TITLE_MAX].strip()


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
    """Srcs that climb out of base_dir; a zip entry cannot safely point there."""
    base = Path(base_dir).resolve()
    return [image.src for image in images if not image.path.is_relative_to(base)]


def write_notion_zip(
    markdown: str,
    images: list[LocalImage],
    base_dir: Path,
    dest: Path,
    fallback_stem: str,
) -> None:
    """Write the zip. Images must exist and lie inside base_dir."""
    stem, body = split_title(markdown, fallback_stem)
    base = Path(base_dir).resolve()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    tmp = dest.with_name(dest.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{stem}.md", unwrap(body))
        # Two srcs can name one file (figures/x.png and ./figures/x.png).
        for path in dict.fromkeys(image.path for image in images):
            zf.write(path, path.relative_to(base).as_posix())
    tmp.replace(dest)
