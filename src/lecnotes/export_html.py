"""Markdown to one self-contained HTML file.

Everything the page needs is inside it: figures as data URIs, styles inline, no
scripts, no requests. It renders the same offline, forever.
"""

import base64
import posixpath
from pathlib import Path
from urllib.parse import unquote

from markdown_it.common.utils import escapeHtml

from .markdown_doc import IMAGE_TYPES, is_external
from .mdparse import new_parser

_CSS = """
:root {
  --bg: #fdfcf9; --fg: #1d1d1b; --muted: #5f5e5a; --rule: #e3e0d8;
  --code-bg: #f1efe9; --link: #1f5fa8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161615; --fg: #e8e6e1; --muted: #a3a19b; --rule: #34332f;
    --code-bg: #22211f; --link: #7fb0ea;
  }
}
* { box-sizing: border-box; }
html { background: var(--bg); }
body {
  margin: 0 auto; max-width: 46rem; padding: 3rem 1.25rem 5rem;
  color: var(--fg); background: var(--bg);
  font: 17px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
}
h1, h2, h3, h4 { line-height: 1.25; margin: 2.2em 0 0.6em; }
h1 { font-size: 2rem; margin-top: 0; }
h2 { font-size: 1.45rem; padding-bottom: 0.3em; border-bottom: 1px solid var(--rule); }
h3 { font-size: 1.15rem; }
a { color: var(--link); }
p, ul, ol, table, pre, blockquote, figure { margin: 0 0 1.1em; }
blockquote {
  margin-left: 0; padding: 0.2em 1em; color: var(--muted);
  border-left: 3px solid var(--rule);
}
code {
  font: 0.88em/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--code-bg); padding: 0.1em 0.3em; border-radius: 4px;
}
pre { background: var(--code-bg); padding: 0.9em 1em; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--rule); padding: 0.4em 0.7em; text-align: left; vertical-align: top; }
th { background: var(--code-bg); }
img { max-width: 100%; height: auto; }
figure { margin: 1.6em 0; text-align: center; }
figure img { border: 1px solid var(--rule); border-radius: 4px; background: #fff; }
figcaption { margin-top: 0.5em; font-size: 0.9rem; color: var(--muted); }
hr { border: none; border-top: 1px solid var(--rule); margin: 2.5em 0; }
@media print {
  body { max-width: none; padding: 0; font-size: 11pt; }
  figure, table, pre, blockquote { break-inside: avoid; }
  h1, h2, h3 { break-after: avoid; }
}
"""


def _data_uri(src: str, path: Path) -> str:
    # The type follows the link's extension, as in markdown_doc.LocalImage.mime.
    mime = IMAGE_TYPES[posixpath.splitext(src)[1].lower()]
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _paragraph_open(self, tokens, idx, options, env):
    if tokens[idx].meta.get("figure"):
        return "<figure>"
    return self.renderToken(tokens, idx, options, env)


def _paragraph_close(self, tokens, idx, options, env):
    token = tokens[idx]
    if token.meta.get("figure"):
        caption = token.meta.get("caption", "")
        figcaption = f"<figcaption>{escapeHtml(caption)}</figcaption>" if caption else ""
        return f"{figcaption}</figure>\n"
    return self.renderToken(tokens, idx, options, env)


def render_html(markdown: str, base_dir: Path, title_fallback: str) -> str:
    """Render to a complete HTML page. Every local image must already exist."""
    md = new_parser()  # a fresh instance: the render rules below must not leak
    md.add_render_rule("paragraph_open", _paragraph_open)
    md.add_render_rule("paragraph_close", _paragraph_close)

    base = Path(base_dir).resolve()
    tokens = md.parse(markdown)
    title = None

    for i, token in enumerate(tokens):
        if (
            title is None
            and token.type == "heading_open"
            and token.tag == "h1"
            and token.level == 0  # not a heading quoted inside a blockquote or list
        ):
            title = md.renderer.renderInlineAsText(tokens[i + 1].children or [], md.options, {})

        if token.type != "inline" or not token.children:
            continue

        for child in token.children:
            if child.type == "image":
                src = child.attrGet("src") or ""
                if src and not is_external(src):
                    path = unquote(src)
                    child.attrSet("src", _data_uri(path, (base / path).resolve()))

        opener, closer = tokens[i - 1], tokens[i + 1]
        only_an_image = len(token.children) == 1 and token.children[0].type == "image"
        # Hidden paragraphs are tight-list items; a figure block would break the list.
        if only_an_image and opener.type == "paragraph_open" and not opener.hidden:
            opener.meta["figure"] = True
            closer.meta["figure"] = True
            closer.meta["caption"] = md.renderer.renderInlineAsText(
                token.children[0].children or [], md.options, {}
            )

    body = md.renderer.render(tokens, md.options, {})
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escapeHtml(title or title_fallback)}</title>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n<body>\n"
        f"{body}"
        "</body>\n</html>\n"
    )
