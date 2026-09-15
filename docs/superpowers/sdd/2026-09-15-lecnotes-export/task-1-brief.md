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

