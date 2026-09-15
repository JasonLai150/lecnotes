"""The vendored KaTeX renderer, prepared for inlining into one HTML file."""

import base64
import re
from functools import lru_cache
from importlib.resources import files

KATEX_VERSION = "0.18.7"

# Each @font-face lists woff2, woff and ttf. Keep only woff2 (every current browser
# reads it), inlined, so the page never asks for a file.
_FONT_SOURCES = re.compile(
    r'src:url\(fonts/(KaTeX_[A-Za-z0-9_-]+)\.woff2\) format\("woff2"\)[^;}]*'
)


def _root():
    return files("lecnotes.vendor.katex")


@lru_cache(maxsize=1)
def katex_css() -> str:
    css = _root().joinpath("katex.min.css").read_text(encoding="utf-8")

    def inline(match: re.Match) -> str:
        data = _root().joinpath("fonts", f"{match.group(1)}.woff2").read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        return f'src:url(data:font/woff2;base64,{encoded}) format("woff2")'

    return _FONT_SOURCES.sub(inline, css)


@lru_cache(maxsize=1)
def katex_js() -> str:
    return _root().joinpath("katex.min.js").read_text(encoding="utf-8")
