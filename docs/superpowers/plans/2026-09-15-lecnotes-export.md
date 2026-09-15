# lecnotes export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `lecnotes export <workdir | file.md> --to html|notion [-o OUT] [--json]`, producing a self-contained HTML file or an import-ready Notion zip from Markdown notes.

**Architecture:** One shared markdown-it-py parser configuration (`mdparse.py`) is used by `finish`'s figure validation and by both exporters, so everything agrees on what an image link is. Leaf modules (`markdown_doc`, `export_html`, `export_notion`) return data and never raise `LecnotesError`; `commands.export` resolves the input, validates, raises errors, and dispatches — the same split `finish` already uses. `cli.py` only adds a subparser and a reporter.

**Tech Stack:** Python 3.11+, pymupdf, markdown-it-py (already a dependency as of commit 69f07a9), pytest, uv.

**Spec:** `docs/superpowers/specs/2026-09-15-lecnotes-export-design.md` (read its "Amendments during planning" section too), extending `docs/superpowers/specs/2026-08-27-lecnotes-design.md`.

## Global Constraints

- Runtime dependencies are exactly `pymupdf` and `markdown-it-py`. Add no others.
- The Markdown is the source of truth: exporters never modify the input `.md`, `NOTES.md`, or anything in `pages/`.
- `export` makes **no network requests**; remote (`http://`, `https://`, `//`) and `data:` images are never fetched and are left untouched.
- Supported local image types (case-insensitive): `.png` → `image/png`, `.jpg`/`.jpeg` → `image/jpeg`, `.gif` → `image/gif`, `.svg` → `image/svg+xml`, `.webp` → `image/webp`.
- New error codes, all exit 1: `not_finished`, `image_not_found`, `image_outside_root`. Reused: `source_not_found`, `unsupported_format`.
- All validation happens **before** any output is written. Outputs overwrite existing files.
- HTML output: no JavaScript, no external stylesheets/fonts/requests, raw HTML in Markdown escaped, `<meta charset="utf-8">`.
- Notion zip: Markdown entry named from the first level-1 heading (sanitized: `/ \ : * ? " < > |` → `-`, trimmed, capped at 100 chars, empty → original stem), that heading removed from the body; images at their paths relative to the Markdown's directory.
- `LecnotesError` is raised only from `commands.py` and `ingest.py`/`workdir.py` (existing). New leaf modules raise nothing.
- Exit codes: `0` success, `1` usage or validation failure, `2` missing external dependency.
- Commit after every task on `main`; do not push; do not commit anything under `docs/superpowers/sdd/`. Commit messages end with `Co-Authored-By: Claude <model name> <noreply@anthropic.com>` then `Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy`.
- Full test suite passes with no warnings after every task.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/lecnotes/mdparse.py` (new) | `new_parser()`, shared `PARSER`, `inline_tokens()` — the one markdown-it configuration |
| `src/lecnotes/figures.py` (modify) | uses `mdparse` instead of its own `_MD` instance |
| `src/lecnotes/markdown_doc.py` (new) | `find_images`, `is_external`, `LocalImage`, `local_images`, `missing_images`, `IMAGE_TYPES` |
| `src/lecnotes/export_html.py` (new) | `render_html(markdown, base_dir, title_fallback) -> str` |
| `src/lecnotes/export_notion.py` (new) | `unwrap`, `sanitize_filename`, `split_title`, `images_outside`, `write_notion_zip` |
| `src/lecnotes/commands.py` (modify) | `export(target, fmt, out=None) -> dict` and its input resolution |
| `src/lecnotes/cli.py` (modify) | `export` subparser, `_report_export` |
| `tests/conftest.py` (modify) | `make_png` helper + `png` fixture |
| `tests/test_mdparse.py`, `tests/test_markdown_doc.py`, `tests/test_export_html.py`, `tests/test_export_notion.py`, `tests/test_export.py` (new) | unit/integration tests |
| `tests/test_cli.py` (modify) | export CLI tests + three new `ERROR_SCENARIOS` |
| `README.md` (modify) | an "Export" section |

Dependency direction: `cli` → `commands` → {`markdown_doc`, `export_html`, `export_notion`, `figures`} → `mdparse`. Nothing imports `commands` or `cli`.

---

### Task 1: Shared Markdown parser

**Files:**
- Create: `src/lecnotes/mdparse.py`
- Modify: `src/lecnotes/figures.py` (remove the module-level `_MD = MarkdownIt(...)` and its imports; iterate via `mdparse.inline_tokens`)
- Test: `tests/test_mdparse.py`

**Interfaces:**
- Consumes: nothing new
- Produces:
  - `new_parser() -> markdown_it.MarkdownIt` — a fresh instance: CommonMark preset, `html` disabled, `table` and `strikethrough` enabled
  - `PARSER: MarkdownIt` — module-level instance from `new_parser()`, for parsing only (never add render rules to it)
  - `inline_tokens(markdown: str, parser: MarkdownIt = PARSER) -> Iterator[Token]` — every child token of every `inline` block token, in document order

- [ ] **Step 1: Write the failing test**

Create `tests/test_mdparse.py`:

```python
from lecnotes import mdparse


def test_new_parser_returns_independent_instances():
    assert mdparse.new_parser() is not mdparse.new_parser()


def test_parser_renders_tables_and_strikethrough():
    md = "| a | b |\n|---|---|\n| 1 | 2 |\n\n~~gone~~\n"
    html = mdparse.PARSER.render(md)
    assert "<table>" in html
    assert "<s>gone</s>" in html


def test_parser_escapes_raw_html():
    html = mdparse.PARSER.render("<script>alert(1)</script>\n")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_inline_tokens_yields_images_in_order():
    md = "![a](one.png) text ![b](two.png)\n\n| x |\n|---|\n| ![c](three.png) |\n"
    srcs = [t.attrGet("src") for t in mdparse.inline_tokens(md) if t.type == "image"]
    assert srcs == ["one.png", "two.png", "three.png"]


def test_inline_tokens_never_yields_code():
    md = "`![a](one.png)`\n\n```\n![b](two.png)\n```\n\n    ![c](three.png)\n"
    types = {t.type for t in mdparse.inline_tokens(md)}
    assert "image" not in types
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mdparse.py -v`
Expected: FAIL with `ImportError: cannot import name 'mdparse'`

- [ ] **Step 3: Implement**

Create `src/lecnotes/mdparse.py`:

```python
"""The one Markdown parser configuration.

finish's figure validation and both exporters parse with this, so they can never
disagree about what counts as an image link.
"""

from collections.abc import Iterator

from markdown_it import MarkdownIt
from markdown_it.token import Token


def new_parser() -> MarkdownIt:
    """A fresh parser. Take one whenever you need to add render rules."""
    return MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])


# Shared for parsing only. Adding render rules to it would leak into every caller.
PARSER = new_parser()


def inline_tokens(markdown: str, parser: MarkdownIt = PARSER) -> Iterator[Token]:
    """Every inline child token (text, image, link_open, ...) in document order.

    Code spans, fenced code and indented code never produce image, link, or text
    children, so example links inside code are invisible here.
    """
    for block in parser.parse(markdown):
        if block.type == "inline" and block.children:
            yield from block.children
```

In `src/lecnotes/figures.py`: delete `from markdown_it import MarkdownIt` and the `_MD = MarkdownIt("commonmark", {"html": False})` instance (and its comment); import `from .mdparse import inline_tokens`; rewrite `_iter_link_tokens` to:

```python
def _iter_link_tokens(markdown: str) -> Iterator[Token]:
    """Yield inline `image`, `link_open`, and `text` tokens, in document order."""
    for token in inline_tokens(markdown):
        if token.type in ("image", "link_open", "text"):
            yield token
```

Keep the existing docstring's explanation of why code tokens are excluded, adapted to the new body. Leave `find_refs`, `find_malformed`, and all regexes unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_mdparse.py tests/test_figures_refs.py tests/test_finish.py -v`
Expected: PASS. Then `uv run pytest -q` — all pass, no warnings.

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/mdparse.py src/lecnotes/figures.py tests/test_mdparse.py
git commit -m "Share one Markdown parser configuration between finish and export"
```

---

### Task 2: Image links and where they point

**Files:**
- Create: `src/lecnotes/markdown_doc.py`
- Modify: `tests/conftest.py` (add `make_png` and the `png` fixture)
- Test: `tests/test_markdown_doc.py`

**Interfaces:**
- Consumes: `mdparse.inline_tokens`
- Produces:
  - `IMAGE_TYPES: dict[str, str]` — lowercase extension → MIME type (see Global Constraints)
  - `find_images(markdown: str) -> list[str]` — `src` of every image token, document order, de-duplicated, empty srcs dropped
  - `is_external(src: str) -> bool` — True for `http://`, `https://`, `//`, `data:` (case-insensitive)
  - `LocalImage` — frozen dataclass: `src: str` (as written), `path: Path` (absolute, resolved); property `mime -> str | None`
  - `local_images(markdown: str, base_dir: Path) -> list[LocalImage]` — non-external images, `src` percent-decoded and resolved against `base_dir`
  - `missing_images(images: list[LocalImage]) -> list[str]` — `src` of each image that is not an existing file or has an unsupported extension, in the given order
  - `tests/conftest.py`: `make_png(path, width=4, height=3) -> Path` and fixture `png` returning `make_png`

- [ ] **Step 1: Add the PNG helper to conftest**

Append to `tests/conftest.py`:

```python
def make_png(path, width=4, height=3) -> Path:
    """A tiny real PNG, so image tests never need checked-in binaries."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), False)
    pix.clear_with(200)
    pix.save(path)
    return path


@pytest.fixture
def png():
    return make_png
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_markdown_doc.py`:

```python
from lecnotes.markdown_doc import (
    IMAGE_TYPES,
    find_images,
    is_external,
    local_images,
    missing_images,
)


def test_find_images_in_order_deduplicated():
    md = "![a](b.png)\n\n![c](a.png) ![d](b.png)\n"
    assert find_images(md) == ["b.png", "a.png"]


def test_find_images_ignores_code_and_plain_links():
    md = "`![a](x.png)`\n\n```\n![b](y.png)\n```\n\n[not an image](z.png)\n"
    assert find_images(md) == []


def test_find_images_handles_brackets_in_alt_text():
    assert find_images("![E_{x~p}[f(x)]](fig.png)\n") == ["fig.png"]


def test_is_external():
    for src in ["http://a/x.png", "HTTPS://a/x.png", "//cdn/x.png", "data:image/png;base64,AA"]:
        assert is_external(src)
    for src in ["figures/x.png", "./x.png", "../x.png", "/abs/x.png"]:
        assert not is_external(src)


def test_image_types():
    assert IMAGE_TYPES[".png"] == "image/png"
    assert IMAGE_TYPES[".jpeg"] == "image/jpeg"
    assert IMAGE_TYPES[".svg"] == "image/svg+xml"


def test_local_images_resolve_against_base_dir(tmp_path):
    md = "![a](figures/x.png) ![b](https://h/y.png) ![c](./z.png)\n"
    images = local_images(md, tmp_path)
    assert [i.src for i in images] == ["figures/x.png", "./z.png"]
    assert images[0].path == (tmp_path / "figures" / "x.png").resolve()
    assert images[1].path == (tmp_path / "z.png").resolve()


def test_local_images_percent_decode(tmp_path):
    images = local_images("![a](<figures/my slide.png>)\n", tmp_path)
    assert images[0].path == (tmp_path / "figures" / "my slide.png").resolve()


def test_mime_is_case_insensitive(tmp_path):
    images = local_images("![a](X.PNG) ![b](y.bmp)\n", tmp_path)
    assert images[0].mime == "image/png"
    assert images[1].mime is None


def test_missing_images_lists_missing_and_unsupported_in_order(tmp_path, png):
    png(tmp_path / "figures" / "ok.png")
    (tmp_path / "old.bmp").write_bytes(b"BM")
    md = "![a](figures/gone.png) ![b](figures/ok.png) ![c](old.bmp) ![d](also-gone.jpg)\n"
    assert missing_images(local_images(md, tmp_path)) == [
        "figures/gone.png",
        "old.bmp",
        "also-gone.jpg",
    ]


def test_directory_named_like_an_image_is_missing(tmp_path):
    (tmp_path / "dir.png").mkdir()
    assert missing_images(local_images("![a](dir.png)\n", tmp_path)) == ["dir.png"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_markdown_doc.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.markdown_doc'`

- [ ] **Step 4: Implement**

Create `src/lecnotes/markdown_doc.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_markdown_doc.py -v` → PASS. Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 6: Commit**

```bash
git add src/lecnotes/markdown_doc.py tests/test_markdown_doc.py tests/conftest.py
git commit -m "Find image links in Markdown and resolve them on disk"
```

---

### Task 3: Self-contained HTML rendering

**Files:**
- Create: `src/lecnotes/export_html.py`
- Test: `tests/test_export_html.py`

**Interfaces:**
- Consumes: `mdparse.new_parser`, `markdown_doc.IMAGE_TYPES`, `markdown_doc.is_external`, `tests/conftest.py` `png` fixture
- Produces: `render_html(markdown: str, base_dir: Path, title_fallback: str) -> str`. Precondition: every local image exists with a supported type (the caller validates). Pure: reads image files, writes nothing.

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_html.py`:

```python
import base64

from lecnotes.export_html import render_html


def test_local_image_is_embedded_as_data_uri(tmp_path, png):
    data = png(tmp_path / "figures" / "slide-001.png").read_bytes()
    html = render_html("![a node](figures/slide-001.png)\n", tmp_path, "notes")
    assert f'src="data:image/png;base64,{base64.b64encode(data).decode()}"' in html
    assert 'src="figures/' not in html


def test_image_only_paragraph_becomes_figure_with_caption(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("Intro.\n\n![The B+ tree root](f.png)\n", tmp_path, "notes")
    assert "<figure><img" in html
    assert "<figcaption>The B+ tree root</figcaption></figure>" in html
    assert "<p>Intro.</p>" in html


def test_empty_alt_gives_figure_without_caption(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("![](f.png)\n", tmp_path, "notes")
    assert "<figure><img" in html
    assert "<figcaption>" not in html


def test_caption_is_escaped(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("![a < b & c](f.png)\n", tmp_path, "notes")
    assert "<figcaption>a &lt; b &amp; c</figcaption>" in html


def test_inline_image_stays_inline(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("See ![icon](f.png) here.\n", tmp_path, "notes")
    assert "<figure>" not in html
    assert html.count("<p>See <img") == 1


def test_tight_list_image_is_not_a_figure(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("- ![icon](f.png)\n- two\n", tmp_path, "notes")
    assert "<figure>" not in html


def test_tables_render(tmp_path):
    html = render_html("| a | b |\n|---|---|\n| 1 | 2 |\n", tmp_path, "notes")
    assert "<table>" in html and "<td>2</td>" in html


def test_raw_html_is_escaped(tmp_path):
    html = render_html("<script>alert(1)</script>\n", tmp_path, "notes")
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_remote_and_data_images_untouched(tmp_path):
    md = "![r](https://example.com/x.png)\n\n![d](data:image/png;base64,AAAA)\n"
    html = render_html(md, tmp_path, "notes")
    assert 'src="https://example.com/x.png"' in html
    assert 'src="data:image/png;base64,AAAA"' in html


def test_title_from_first_h1(tmp_path):
    html = render_html("## Not this\n\n# B+ *Trees*\n\n# Later\n", tmp_path, "notes")
    assert "<title>B+ Trees</title>" in html


def test_title_falls_back_and_is_escaped(tmp_path):
    assert "<title>lec&lt;1&gt;</title>" in render_html("no heading\n", tmp_path, "lec<1>")


def test_page_shell_is_self_contained(tmp_path):
    html = render_html("# T\n\ntext\n", tmp_path, "notes")
    assert html.startswith("<!doctype html>")
    assert '<meta charset="utf-8">' in html
    assert '<meta name="viewport"' in html
    assert "<style>" in html
    assert "prefers-color-scheme: dark" in html
    assert "@media print" in html
    for forbidden in ("<script", "<link", "@import", "http://", "https://"):
        assert forbidden not in html


def test_jpeg_uses_jpeg_mime(tmp_path, png):
    # The bytes are PNG, but the mime type follows the extension.
    png(tmp_path / "photo.JPG")
    assert 'src="data:image/jpeg;base64,' in render_html("![p](photo.JPG)\n", tmp_path, "n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_html.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.export_html'`

- [ ] **Step 3: Implement**

Create `src/lecnotes/export_html.py`:

```python
"""Markdown to one self-contained HTML file.

Everything the page needs is inside it: figures as data URIs, styles inline, no
scripts, no requests. It renders the same offline, forever.
"""

import base64
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


def _data_uri(path: Path) -> str:
    mime = IMAGE_TYPES[path.suffix.lower()]
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
        if title is None and token.type == "heading_open" and token.tag == "h1":
            title = md.renderer.renderInlineAsText(tokens[i + 1].children or [], md.options, {})

        if token.type != "inline" or not token.children:
            continue

        for child in token.children:
            if child.type == "image":
                src = child.attrGet("src") or ""
                if src and not is_external(src):
                    child.attrSet("src", _data_uri((base / unquote(src)).resolve()))

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_html.py -v` → PASS. If `renderInlineAsText` or `add_render_rule` behave differently in the installed markdown-it-py version, keep the behavior the tests pin down and note the deviation in the report. Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/export_html.py tests/test_export_html.py
git commit -m "Render Markdown to a self-contained HTML page"
```

---

### Task 4: Notion import zip

**Files:**
- Create: `src/lecnotes/export_notion.py`
- Test: `tests/test_export_notion.py`

**Interfaces:**
- Consumes: `mdparse.PARSER`, `markdown_doc.LocalImage`, `markdown_doc.local_images` (tests only), `png` fixture
- Produces:
  - `TITLE_MAX = 100`
  - `unwrap(markdown: str) -> str`
  - `sanitize_filename(text: str) -> str` (may return `""`)
  - `split_title(markdown: str, fallback_stem: str) -> tuple[str, str]` — `(file stem, body with that heading removed)`
  - `images_outside(images: list[LocalImage], base_dir: Path) -> list[str]` — srcs resolving outside `base_dir`, in order
  - `write_notion_zip(markdown: str, images: list[LocalImage], base_dir: Path, dest: Path, fallback_stem: str) -> None` — precondition: images exist and none are outside `base_dir`

**How unwrap works (and why not a line regex):** parse with `PARSER`; every top-level-or-list `paragraph_open` token that is *not* inside a blockquote and whose `map` spans more than one source line has its lines joined — continuation lines are stripped and appended to the previous line with one space. A line ending in a hard break (two trailing spaces or a backslash) is not joined onto. Because only paragraph line ranges are touched, fenced code, indented code, tables, headings, and blockquotes are left byte-for-byte. This replaces CS4440's line-regex `unwrap` with the same intent.

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_notion.py`:

```python
import zipfile

from lecnotes.export_notion import (
    TITLE_MAX,
    images_outside,
    sanitize_filename,
    split_title,
    unwrap,
    write_notion_zip,
)
from lecnotes.markdown_doc import local_images


def test_unwrap_joins_wrapped_paragraph_keeping_spans_intact():
    md = "A **bold\nclaim** that\nwraps.\n\nNext para.\n"
    assert unwrap(md) == "A **bold claim** that wraps.\n\nNext para.\n"


def test_unwrap_joins_list_item_continuations():
    md = "- first item\n  continues here\n- second\n"
    assert unwrap(md) == "- first item continues here\n- second\n"


def test_unwrap_leaves_code_tables_headings_and_quotes_alone():
    md = (
        "# Heading\n\n"
        "```\nline one\nline two\n```\n\n"
        "    indented\n    code\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        "> quoted\n> lines\n"
    )
    assert unwrap(md) == md


def test_unwrap_preserves_hard_breaks():
    md = "line one  \nline two\\\nline three\nline four\n"
    assert unwrap(md) == "line one  \nline two\\\nline three line four\n"


def test_sanitize_filename():
    assert sanitize_filename('  B+ Trees: why/how? "fast" <1> | *2*  ') == 'B+ Trees- why-how- -fast- -1- - -2-'
    assert len(sanitize_filename("x" * 300)) == TITLE_MAX
    assert sanitize_filename("   ") == ""


def test_split_title_uses_first_h1_and_removes_it():
    md = "# Imitation Learning\n\nIntro text.\n\n# Second H1 stays\n"
    stem, body = split_title(md, "lec1")
    assert stem == "Imitation Learning"
    assert body == "Intro text.\n\n# Second H1 stays\n"


def test_split_title_strips_inline_markup():
    stem, _ = split_title("# B+ *Trees*\n\ntext\n", "lec1")
    assert stem == "B+ Trees"


def test_split_title_falls_back_without_h1():
    md = "## Only h2\n\ntext\n"
    assert split_title(md, "lec1") == ("lec1", md)


def test_split_title_falls_back_when_title_sanitizes_to_empty():
    stem, body = split_title("# ///\n\ntext\n", "lec1")
    assert stem == "---"  # slashes become dashes, which is not empty
    stem, body = split_title("#    \n\ntext\n", "lec1")
    assert stem == "lec1"


def test_images_outside(tmp_path, png):
    notes = tmp_path / "notes"
    notes.mkdir()
    md = "![a](figures/x.png) ![b](../shared/y.png) ![c](./z.png)\n"
    assert images_outside(local_images(md, notes), notes) == ["../shared/y.png"]


def test_write_notion_zip_layout(tmp_path, png):
    base = tmp_path / "out"
    png(base / "figures" / "slide-001.png")
    png(base / "figures" / "slide-002.png")
    md = (
        "# Learning from Data\n\n"
        "Some wrapped\nprose.\n\n"
        "![one](figures/slide-001.png)\n\n"
        "![two](./figures/slide-002.png)\n\n"
        "![one again](figures/slide-001.png)\n"
    )
    dest = base / "lec1-notion.zip"
    write_notion_zip(md, local_images(md, base), base, dest, "lec1")

    with zipfile.ZipFile(dest) as zf:
        assert sorted(zf.namelist()) == [
            "Learning from Data.md",
            "figures/slide-001.png",
            "figures/slide-002.png",
        ]
        text = zf.read("Learning from Data.md").decode("utf-8")
    assert not text.startswith("# Learning from Data")
    assert "Some wrapped prose." in text
    assert "![one](figures/slide-001.png)" in text
    assert not (base / "lec1-notion.zip.tmp").exists()


def test_write_notion_zip_overwrites(tmp_path):
    dest = tmp_path / "n.zip"
    dest.write_bytes(b"old")
    write_notion_zip("# T\n\nbody\n", [], tmp_path, dest, "n")
    with zipfile.ZipFile(dest) as zf:
        assert zf.namelist() == ["T.md"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_notion.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.export_notion'`

- [ ] **Step 3: Implement**

Create `src/lecnotes/export_notion.py`:

```python
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
```

Note on `test_split_title_falls_back_when_title_sanitizes_to_empty`: `# ///` sanitizes to `---` (not empty), and a heading with only whitespace has empty text, which falls back.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_notion.py -v` → PASS. If markdown-it's `map` for a list-item paragraph differs from the test's expectation, keep the tested behavior (wrapped continuation lines joined onto the item line) and report the deviation. Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/export_notion.py tests/test_export_notion.py
git commit -m "Package Markdown and its images as a Notion import zip"
```

---

### Task 5: The export command and CLI

**Files:**
- Modify: `src/lecnotes/commands.py` (add `export` and `_export_source`)
- Modify: `src/lecnotes/cli.py` (add the `export` subparser, dispatch, `_report_export`)
- Test: `tests/test_export.py` (new), `tests/test_cli.py` (modify)

**Interfaces:**
- Consumes: `markdown_doc.local_images`, `markdown_doc.missing_images`, `export_html.render_html`, `export_notion.images_outside`, `export_notion.write_notion_zip`, `workdir.is_workdir`, `workdir.load_manifest`, `workdir.out_dir`, `workdir.notes_path`, `commands.prep`, `commands.finish`, `png` fixture, `synth` fixture
- Produces: `commands.export(target: Path, fmt: str, out: Path | None = None) -> dict` returning `{"ok": True, "format", "source", "output", "images", "bytes"}`; CLI `lecnotes export <source> --to {html,notion} [-o OUT] [--json]`

- [ ] **Step 1: Write the failing command tests**

Create `tests/test_export.py`:

```python
import zipfile

import pytest

from lecnotes import workdir
from lecnotes.commands import export, finish, prep
from lecnotes.errors import LecnotesError


@pytest.fixture
def finished(synth, tmp_path):
    """A prepped and finished 3-slide workdir with one figure."""
    pdf = synth(tmp_path / "lec1.pdf", [{"text": f"S{i}", "small_box": (100, 100, 300, 220)}
                                        for i in range(1, 4)])
    prep(pdf)
    root = tmp_path / "lec1.notes"
    workdir.notes_path(root).write_text(
        "# Lecture One\n\nWrapped\nprose.\n\n![node](figures/slide-002.png)\n", encoding="utf-8"
    )
    finish(root)
    return root


def test_html_from_workdir(finished):
    result = export(finished, "html")
    out = workdir.out_dir(finished) / "lec1.html"
    assert result == {
        "ok": True,
        "format": "html",
        "source": str(workdir.out_dir(finished) / "lec1.md"),
        "output": str(out),
        "images": 1,
        "bytes": out.stat().st_size,
    }
    html = out.read_text(encoding="utf-8")
    assert "data:image/png;base64," in html and "<title>Lecture One</title>" in html


def test_notion_from_workdir(finished):
    result = export(finished, "notion")
    out = workdir.out_dir(finished) / "lec1-notion.zip"
    assert result["output"] == str(out) and result["images"] == 1
    with zipfile.ZipFile(out) as zf:
        assert sorted(zf.namelist()) == ["Lecture One.md", "figures/slide-002.png"]


def test_markdown_file_directly(tmp_path, png):
    png(tmp_path / "img" / "a.png")
    md = tmp_path / "edited.md"
    md.write_text("# E\n\n![a](img/a.png)\n", encoding="utf-8")
    result = export(md, "html")
    assert result["output"] == str(tmp_path / "edited.html")
    assert result["source"] == str(md)


def test_out_option_and_overwrite(tmp_path):
    md = tmp_path / "n.md"
    md.write_text("text\n", encoding="utf-8")
    dest = tmp_path / "deep" / "dir" / "custom.html"
    export(md, "html", out=dest)
    first = dest.read_text()
    md.write_text("changed\n", encoding="utf-8")
    export(md, "html", out=dest)
    assert dest.read_text() != first


def test_source_not_found(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path / "nope.md", "html")
    assert exc.value.code == "source_not_found"


@pytest.mark.parametrize("name", ["notes.txt", "deck.pdf"])
def test_non_markdown_file_is_unsupported(tmp_path, name):
    (tmp_path / name).write_text("x")
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path / name, "html")
    assert exc.value.code == "unsupported_format"


def test_plain_directory_is_unsupported(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path, "html")
    assert exc.value.code == "unsupported_format"


def test_workdir_before_finish(synth, tmp_path):
    prep(synth(tmp_path / "lec1.pdf", [{"text": "a"}]))
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path / "lec1.notes", "html")
    assert exc.value.code == "not_finished"
    assert "finish" in exc.value.message


def test_workdir_with_notes_edited_after_finish(finished):
    workdir.notes_path(finished).write_text("# Lecture One\n\nnewer\n", encoding="utf-8")
    with pytest.raises(LecnotesError) as exc:
        export(finished, "notion")
    assert exc.value.code == "not_finished"
    assert "NOTES.md" in exc.value.message
    assert not (workdir.out_dir(finished) / "lec1-notion.zip").exists()


def test_missing_images_all_listed_nothing_written(tmp_path, png):
    png(tmp_path / "ok.png")
    md = tmp_path / "n.md"
    md.write_text("![a](gone1.png) ![b](ok.png) ![c](gone2.png) ![d](gone1.png)\n")
    with pytest.raises(LecnotesError) as exc:
        export(md, "html")
    assert exc.value.code == "image_not_found"
    assert exc.value.detail["missing"] == ["gone1.png", "gone2.png"]
    assert not (tmp_path / "n.html").exists()


def test_outside_root_rejected_for_notion_only(tmp_path, png):
    png(tmp_path / "shared" / "x.png")
    notes = tmp_path / "notes"
    notes.mkdir()
    md = notes / "n.md"
    md.write_text("![x](../shared/x.png)\n")

    with pytest.raises(LecnotesError) as exc:
        export(md, "notion")
    assert exc.value.code == "image_outside_root"
    assert exc.value.detail["outside"] == ["../shared/x.png"]
    assert not (notes / "n-notion.zip").exists()

    assert export(md, "html")["images"] == 1


def test_exporters_never_modify_the_markdown(finished):
    md = workdir.out_dir(finished) / "lec1.md"
    before = md.read_bytes()
    export(finished, "html")
    export(finished, "notion")
    assert md.read_bytes() == before
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_export.py -v`
Expected: FAIL with `ImportError: cannot import name 'export'`

- [ ] **Step 3: Implement `commands.export`**

Add to the imports at the top of `src/lecnotes/commands.py`:

```python
from .export_html import render_html
from .export_notion import images_outside, write_notion_zip
from .markdown_doc import local_images, missing_images
```

Append to `src/lecnotes/commands.py`:

```python
def _export_source(target: Path) -> Path:
    """The Markdown file to export, from a workdir or a .md path."""
    if not target.exists():
        raise LecnotesError(
            "source_not_found", f"no such file or directory: {target}", path=str(target)
        )

    if target.is_dir():
        if not workdir.is_workdir(target):
            raise LecnotesError(
                "unsupported_format",
                f"{target} is a directory but not a lecnotes workdir; "
                "pass a workdir or a .md file",
                path=str(target),
            )
        deck = workdir.load_manifest(target)["deck"]
        markdown = workdir.out_dir(target) / f"{deck}.md"
        if not markdown.is_file():
            raise LecnotesError(
                "not_finished",
                f"{markdown} does not exist yet; run `lecnotes finish` on this workdir first",
                path=str(target),
            )
        notes = workdir.notes_path(target)
        if notes.is_file() and notes.read_text(encoding="utf-8") != markdown.read_text(
            encoding="utf-8"
        ):
            raise LecnotesError(
                "not_finished",
                "NOTES.md has changed since the last finish; "
                "run `lecnotes finish` again before exporting",
                path=str(target),
            )
        return markdown

    if target.suffix.lower() != ".md":
        raise LecnotesError(
            "unsupported_format",
            f"cannot export {target.name}; pass a lecnotes workdir or a .md file",
            path=str(target),
        )
    return target


def export(target: Path, fmt: str, out: Path | None = None) -> dict:
    source = _export_source(Path(target))
    markdown = source.read_text(encoding="utf-8")
    base_dir = source.parent
    images = local_images(markdown, base_dir)

    # Validate everything before writing anything.
    missing = missing_images(images)
    if missing:
        raise LecnotesError(
            "image_not_found",
            "these images are missing or not a supported type "
            "(png, jpg, jpeg, gif, svg, webp): " + ", ".join(missing),
            missing=missing,
        )

    if fmt == "notion":
        outside = images_outside(images, base_dir)
        if outside:
            raise LecnotesError(
                "image_outside_root",
                "a Notion zip can only include images inside the Markdown file's "
                "folder; move or copy these: " + ", ".join(outside),
                outside=outside,
            )
        dest = Path(out) if out else base_dir / f"{source.stem}-notion.zip"
        write_notion_zip(markdown, images, base_dir, dest, source.stem)
    elif fmt == "html":
        dest = Path(out) if out else base_dir / f"{source.stem}.html"
        html = render_html(markdown, base_dir, source.stem)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
    else:
        raise ValueError(f"unknown export format: {fmt}")

    return {
        "ok": True,
        "format": fmt,
        "source": str(source),
        "output": str(dest),
        "images": len({image.path for image in images}),
        "bytes": dest.stat().st_size,
    }
```

- [ ] **Step 4: Run command tests**

Run: `uv run pytest tests/test_export.py -v` → PASS.
Run: `uv run pytest tests/test_cli.py -v` → `test_every_raised_error_code_has_a_cli_scenario` now FAILS (three new codes have no scenario). That is expected and fixed in Step 5.

- [ ] **Step 5: Write the failing CLI tests**

In `tests/test_cli.py`, add after the `_figure_malformed` scenario function:

```python
def _finished(synth, tmp_path, notes="# T\n\n![a](figures/slide-001.png)\n"):
    pdf, root = _prepped(synth, tmp_path, notes=notes)
    commands.finish(root)
    return root


def _not_finished(tmp_path, synth, monkeypatch):
    _, root = _prepped(synth, tmp_path)
    return ["export", str(root), "--to", "html"]


def _image_not_found(tmp_path, synth, monkeypatch):
    md = tmp_path / "notes.md"
    md.write_text("![x](figures/missing.png)\n")
    return ["export", str(md), "--to", "html"]


def _image_outside_root(tmp_path, synth, monkeypatch):
    from conftest import make_png

    make_png(tmp_path / "shared" / "x.png")
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "n.md").write_text("![x](../shared/x.png)\n")
    return ["export", str(notes / "n.md"), "--to", "notion"]
```

Add three entries to `ERROR_SCENARIOS`:

```python
    "not_finished": (_not_finished, 1),
    "image_not_found": (_image_not_found, 1),
    "image_outside_root": (_image_outside_root, 1),
```

Add these tests (anywhere after the fixtures):

```python
def test_export_html_human_output(synth, tmp_path, capsys):
    root = _finished(synth, tmp_path)
    capsys.readouterr()
    assert main(["export", str(root), "--to", "html"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == str(root / "out" / "lec1.html")
    assert "1 image" in out


def test_export_notion_json(synth, tmp_path, capsys):
    root = _finished(synth, tmp_path)
    capsys.readouterr()
    assert main(["export", str(root), "--to", "notion", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["format"] == "notion"
    assert payload["output"].endswith("lec1-notion.zip")
    assert payload["images"] == 1 and payload["bytes"] > 0


def test_export_requires_to(tmp_path, capsys):
    md = tmp_path / "n.md"
    md.write_text("x\n")
    assert main(["export", str(md)]) == 1
    assert "--to" in capsys.readouterr().err


def test_export_rejects_unknown_format(tmp_path, capsys):
    md = tmp_path / "n.md"
    md.write_text("x\n")
    assert main(["export", str(md), "--to", "pdf"]) == 1
```

If `from conftest import make_png` does not import under this project's pytest configuration, request the `png` fixture instead by changing the scenario signature is not possible (scenarios share one signature) — so in that case add `import pymupdf` at the top of `test_cli.py` and build the PNG inline exactly as `make_png` does.

- [ ] **Step 6: Run to verify failure**

Run: `uv run pytest tests/test_cli.py -v`
Expected: the new export tests and the three new parametrized scenarios FAIL (`invalid choice: 'export'`).

- [ ] **Step 7: Implement the CLI**

In `src/lecnotes/cli.py`, import `export` alongside `prep` and `finish` (`from .commands import export, finish, prep`). In `_build_parser`, after the `finish` subparser:

```python
    e = sub.add_parser("export", help="convert finished notes to HTML or a Notion import zip")
    e.add_argument("source", type=Path, help="a finished workdir, or any .md file")
    e.add_argument(
        "--to", dest="fmt", required=True, choices=["html", "notion"], help="output format"
    )
    e.add_argument("-o", "--out", type=Path, default=None, help="output file path")
    e.add_argument("--json", action="store_true", help="machine-readable output")
```

Add the reporter next to the others:

```python
def _report_export(result: dict) -> None:
    size = result["bytes"]
    human = f"{size / 1_048_576:.1f} MB" if size >= 1_048_576 else f"{size / 1024:.0f} KB"
    noun = "image" if result["images"] == 1 else "images"
    print(f"{result['output']}")
    print(f"  {result['images']} {noun}, {human}")
```

In `main`, replace the `if/else` dispatch with:

```python
        if args.command == "prep":
            result = prep(args.source, out=args.out, force=args.force)
            reporter = _report_prep
        elif args.command == "finish":
            result = finish(args.workdir)
            reporter = _report_finish
        else:
            result = export(args.source, args.fmt, out=args.out)
            reporter = _report_export
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py tests/test_export.py -v` → PASS. Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 9: Commit**

```bash
git add src/lecnotes/commands.py src/lecnotes/cli.py tests/test_export.py tests/test_cli.py
git commit -m "Add lecnotes export --to html|notion"
```

---

### Task 6: README and a real export

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the finished CLI
- Produces: nothing importable

- [ ] **Step 1: Export real lecture notes**

The real notes live in the user's workdir `DRL lectures/lec-1-cs8803-drl-f26-supervised-learning.notes` inside the repo (git-ignored). Do not modify anything in it. Copy it to the scratchpad first, then export the copy:

```bash
SCRATCH=/private/tmp/claude-501/-Users-jasonlai150-Documents-GitHub-4440/b8ce7be5-28b5-4a05-868b-6c0cf5495ca3/scratchpad
rm -rf "$SCRATCH/export-e2e" && mkdir -p "$SCRATCH/export-e2e"
cp -R "/Users/jasonlai150/Documents/GitHub/lecnotes/DRL lectures/lec-1-cs8803-drl-f26-supervised-learning.notes" "$SCRATCH/export-e2e/"
cd "$SCRATCH/export-e2e/lec-1-cs8803-drl-f26-supervised-learning.notes"
uv --project /Users/jasonlai150/Documents/GitHub/lecnotes run lecnotes export . --to html --json
uv --project /Users/jasonlai150/Documents/GitHub/lecnotes run lecnotes export . --to notion --json
```

If `export` reports `not_finished`, run `lecnotes finish .` on the **copy** and retry. Record every command and its output.

Then verify:
- the HTML has as many `data:image/png;base64,` occurrences as the notes have distinct figure links (`grep -o 'data:image/png;base64,' out/*.html | wc -l`), no `src="figures/`, and no `http`;
- `unzip -l out/*-notion.zip` lists one `.md` named after the notes' first heading plus every `figures/slide-NNN.png`;
- the `.md` inside the zip (`unzip -p out/*-notion.zip '*.md' | head -20`) starts after the title and has no hard-wrapped paragraphs.

- [ ] **Step 2: Add an Export section to README.md**

Add after the section that documents `finish` (keep the rest of the README unchanged):

````markdown
## Export

The Markdown `finish` writes is the source of truth. `export` turns it into
something easier to read or share, without changing it:

```sh
lecnotes export lec13.notes --to html     # lec13.notes/out/lec13.html
lecnotes export lec13.notes --to notion   # lec13.notes/out/lec13-notion.zip
```

- **HTML** is one self-contained file: figures are embedded, styles are inline,
  there is no JavaScript and nothing loads from the network. Open it in any
  browser, or print it to PDF.
- **Notion**: in Notion, go to Settings → Import → Markdown and choose the zip.
  The page is named after the notes' title, and figures come through. (Pasting
  the `.md` alone loses the images; the zip keeps them together.)

`export` also accepts any `.md` file, resolving images relative to it, and `-o`
sets the output path. On a workdir it refuses to export notes that have changed
since the last `finish`, so you never share a stale copy.
````

Also add the three new codes to any error-code list in the README, if the README has one.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Document export"
```

---

## Verification

- [ ] `uv run pytest -q` passes with no warnings
- [ ] `uv run lecnotes export --help` renders
- [ ] Task 6's real export produced an HTML file with every figure embedded and a zip with the titled `.md` plus all figures
