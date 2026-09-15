"""Image links in a Markdown document, and where they point on disk.

Returns findings only. Deciding which findings are errors is commands.py's job.
"""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from .mdparse import inline_tokens

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}

_EXTERNAL_PREFIXES = ("http://", "https://", "//", "data:")


def find_images(markdown: str) -> list[str]:
    """Every image src, in document order, de-duplicated."""
    seen: dict[str, None] = {}
    for token in inline_tokens(markdown):
        if token.type == "image":
            src = token.attrGet("src") or ""
            if src:
                seen.setdefault(src, None)
    return list(seen)


def is_external(src: str) -> bool:
    """Remote or inline images: never fetched, never packaged, left as written."""
    return src.lower().startswith(_EXTERNAL_PREFIXES)


@dataclass(frozen=True)
class LocalImage:
    src: str  # as it appears in the parsed Markdown
    path: Path  # absolute and resolved

    @property
    def mime(self) -> str | None:
        return IMAGE_TYPES.get(self.path.suffix.lower())


def local_images(markdown: str, base_dir: Path) -> list[LocalImage]:
    base = Path(base_dir).resolve()
    return [
        # markdown-it percent-encodes link targets; the file on disk is not encoded.
        LocalImage(src=src, path=(base / unquote(src)).resolve())
        for src in find_images(markdown)
        if not is_external(src)
    ]


def missing_images(images: list[LocalImage]) -> list[str]:
    """Srcs that are not an existing file of a supported image type."""
    return [image.src for image in images if image.mime is None or not image.path.is_file()]
