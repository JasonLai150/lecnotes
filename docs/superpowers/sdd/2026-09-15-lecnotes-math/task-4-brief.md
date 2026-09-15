### Task 4: Render math in the HTML export

**Files:**
- Modify: `src/lecnotes/export_html.py`
- Test: `tests/test_export_html.py`

**Interfaces:**
- Consumes: `mdparse.new_parser` (with math), `mdparse.inline_text`, `katex.katex_css`, `katex.katex_js`
- Produces: `render_html(markdown, base_dir, title_fallback) -> str` (signature unchanged)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_export_html.py`:

```python
MATH_MD = (
    "# Policy $\\pi$ gradients\n\n"
    "Inline $a<b$ and $$x^2$$ here.\n\n"
    "$$\n\\nabla_\\theta J(\\theta)\n$$\n"
)


def test_inline_math_is_escaped_latex_in_a_span(tmp_path):
    html = render_html(MATH_MD, tmp_path, "n")
    assert '<span class="lecnotes-math">a&lt;b</span>' in html


def test_display_math_uses_a_display_div(tmp_path):
    html = render_html(MATH_MD, tmp_path, "n")
    assert '<div class="lecnotes-math lecnotes-math-display">x^2</div>' in html
    assert '<div class="lecnotes-math lecnotes-math-display">\\nabla_\\theta J(\\theta)</div>' in html


def test_katex_is_inlined_only_with_math(tmp_path):
    from lecnotes.katex import katex_js

    with_math = render_html(MATH_MD, tmp_path, "n")
    assert katex_js() in with_math
    assert "throwOnError: false" in with_math and "trust: false" in with_math

    without = render_html("# Plain\n\ntext\n", tmp_path, "n")
    assert "<script" not in without
    assert "katex" not in without.lower()


def test_math_page_makes_no_external_loads(tmp_path):
    html = render_html(MATH_MD, tmp_path, "n")
    for forbidden in ('src="http', "src='http", 'href="http', "url(http", "url(fonts/", "@import", "<link"):
        assert forbidden not in html


def test_title_and_caption_keep_math_source(tmp_path, png):
    png(tmp_path / "f.png")
    html = render_html("# The $\\pi$ policy\n\n![cap $\\theta$](f.png)\n", tmp_path, "n")
    assert "<title>The \\pi policy</title>" in html
    assert "<figcaption>cap \\theta</figcaption>" in html


def test_math_in_code_is_code(tmp_path):
    html = render_html("`$x$`\n\n```\n$$y$$\n```\n", tmp_path, "n")
    assert "lecnotes-math" not in html
    assert "<script" not in html
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_export_html.py -v` → new tests FAIL.

- [ ] **Step 3: Implement**

In `src/lecnotes/export_html.py`:

1. Imports: `from .katex import katex_css, katex_js` and change `from .mdparse import new_parser` to `from .mdparse import inline_text, new_parser`.

2. Add after `_CSS`:

```python
_MATH_CSS = """
.lecnotes-math-display { display: block; margin: 1.2em 0; overflow-x: auto; overflow-y: hidden; }
"""

# Render every math element in place. throwOnError: false shows a bad formula's
# source in red instead of breaking the page; trust: false blocks \href and friends.
_RENDER_MATH = """
document.querySelectorAll(".lecnotes-math").forEach(function (el) {
  katex.render(el.textContent, el, {
    displayMode: el.classList.contains("lecnotes-math-display"),
    throwOnError: false,
    trust: false
  });
});
"""

_MATH_TOKENS = ("math_inline", "math_inline_double", "math_block")


def _math_inline(self, tokens, idx, options, env):
    return f'<span class="lecnotes-math">{escapeHtml(tokens[idx].content)}</span>'


def _math_display(self, tokens, idx, options, env):
    latex = escapeHtml(tokens[idx].content.strip())
    return f'<div class="lecnotes-math lecnotes-math-display">{latex}</div>\n'
```

3. In `render_html`, after the paragraph render rules:

```python
    md.add_render_rule("math_inline", _math_inline)
    md.add_render_rule("math_inline_double", _math_display)
    md.add_render_rule("math_block", _math_display)
```

4. Replace both `md.renderer.renderInlineAsText(...)` calls (title and caption) with `inline_text(...)` on the same children lists.

5. Track math: before the loop set `has_math = False`; inside the loop, before `if token.type != "inline"`, add
```python
        if token.type in _MATH_TOKENS or any(
            child.type in _MATH_TOKENS for child in (token.children or [])
        ):
            has_math = True
```

6. Build the page with KaTeX only when `has_math`:

```python
    head_math = f"<style>{katex_css()}{_MATH_CSS}</style>\n" if has_math else ""
    body_math = f"<script>{katex_js()}</script>\n<script>{_RENDER_MATH}</script>\n" if has_math else ""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escapeHtml(title or title_fallback)}</title>\n"
        f"<style>{_CSS}</style>\n"
        f"{head_math}"
        "</head>\n<body>\n"
        f"{body}"
        f"{body_math}"
        "</body>\n</html>\n"
    )
```

`_math_display` strips the block content, so a `$$\n...\n$$` block and `$$x^2$$` render identically.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_export_html.py -v` → PASS (the existing `test_page_shell_is_self_contained` still passes: its document has no math). Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 5: Commit**

Subject: "Render LaTeX math in HTML exports with bundled KaTeX"

---

