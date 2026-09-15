# lecnotes math Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Notes write equations as LaTeX (`$...$`, `$$` blocks); the shared parser understands them; the HTML export renders them with a bundled KaTeX; the Notion export passes them through.

**Architecture:** The dollar-math plugin joins the one shared parser configuration (`mdparse.new_parser`), so `finish`, the HTML exporter and the Notion exporter agree on what math is. KaTeX is vendored as static files inside the package and inlined into HTML only when a document contains math. A new `mdparse.inline_text` keeps math source in titles and captions.

**Tech Stack:** Python 3.11+, pymupdf, markdown-it-py, mdit-py-plugins (new), KaTeX 0.18.7 (vendored files), pytest, uv.

**Spec:** `docs/superpowers/specs/2026-09-15-lecnotes-math-design.md`

## Global Constraints

- Runtime dependencies are exactly `pymupdf`, `markdown-it-py`, `mdit-py-plugins`. KaTeX is vendored files, not a dependency.
- Dollar-math plugin options, exactly: `allow_labels=False, allow_space=False, allow_digits=False, double_inline=True`.
- Math token types: `math_inline`, `math_inline_double`, `math_block`.
- KaTeX version `0.18.7`, vendored at `src/lecnotes/vendor/katex/`: `katex.min.js`, `katex.min.css`, `fonts/*.woff2` (20 files), `LICENSE`, `VERSION`.
- HTML math markup: inline `<span class="lecnotes-math">…</span>`; display `<div class="lecnotes-math lecnotes-math-display">…</div>`; content is the HTML-escaped LaTeX.
- KaTeX render options: `displayMode` from the class, `throwOnError: false`, `trust: false`.
- HTML without math contains no `<script>`. HTML with math makes no external loads (no `src="http`, `href="http`, `url(http`, `url(fonts/`, `@import`, `<link`).
- Leaf modules (`mdparse`, `markdown_doc`, `export_html`, `export_notion`, `figures`, `katex`) never raise `LecnotesError`.
- Commit on `main` after every task; do not push; do not commit `docs/superpowers/sdd/`. Commit messages: subject, blank line, `Co-Authored-By: Claude <model name> <noreply@anthropic.com>`, `Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy`, each on its own line.
- Full suite passes with no warnings after every task.

---

## File Structure

| File | Change |
|---|---|
| `pyproject.toml`, `uv.lock` | add `mdit-py-plugins` |
| `src/lecnotes/mdparse.py` | dollar-math in `new_parser`; new `inline_text` |
| `src/lecnotes/instructions.py` | `{{name}}` placeholders instead of `string.Template` |
| `src/lecnotes/templates/instructions.md` | new Equations section; `{{deck}}`, `{{slides}}`, `{{source_name}}` |
| `src/lecnotes/vendor/__init__.py`, `src/lecnotes/vendor/katex/__init__.py` | new (empty; regular packages for importlib.resources) |
| `src/lecnotes/vendor/katex/*` | vendored KaTeX 0.18.7 |
| `src/lecnotes/katex.py` | new: `KATEX_VERSION`, `katex_css()`, `katex_js()` |
| `src/lecnotes/export_html.py` | math render rules, conditional KaTeX, `inline_text` for title/caption |
| `src/lecnotes/export_notion.py` | `inline_text` for the title |
| `README.md` | math note |
| tests | `test_mdparse.py`, `test_instructions.py`, `test_katex.py` (new), `test_export_html.py`, `test_export_notion.py` |

---

### Task 1: Math in the shared parser

**Files:**
- Modify: `pyproject.toml` (via `uv add mdit-py-plugins`), `uv.lock`
- Modify: `src/lecnotes/mdparse.py`
- Test: `tests/test_mdparse.py`

**Interfaces:**
- Produces: `new_parser()` now also parses dollar math; `inline_text(children: list[Token]) -> str` — plain text of inline tokens: `text` and `code_inline` contribute their content; `math_inline`/`math_inline_double` contribute their LaTeX content; `image` contributes `inline_text` of its children; `softbreak`/`hardbreak` contribute a space; everything else nothing.

- [ ] **Step 1: Add the dependency**

Run: `uv add "mdit-py-plugins>=0.4"` then `uv run python -c "import mdit_py_plugins; print(mdit_py_plugins.__version__)"`.

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_mdparse.py`:

```python
from lecnotes.mdparse import PARSER, inline_text


def _inline_types(md):
    return [(t.type, t.content) for t in mdparse.inline_tokens(md)]


def test_inline_and_double_inline_math():
    kinds = _inline_types(r"Policy $\pi_\theta$ and $$x^2$$ here." + "\n")
    assert ("math_inline", r"\pi_\theta") in kinds
    assert ("math_inline_double", "x^2") in kinds


def test_display_math_block():
    blocks = [t for t in PARSER.parse("Text.\n\n$$\n\\sum_t r_t\n$$\n") if t.type == "math_block"]
    assert len(blocks) == 1
    assert blocks[0].content.strip() == r"\sum_t r_t"


def test_emphasis_characters_stay_inside_math():
    kinds = _inline_types("$a_i * b_j * c$\n")
    assert kinds == [("math_inline", "a_i * b_j * c")]


def test_prices_spaces_and_code_are_not_math():
    # Separate paragraphs, so one case's dollar can't pair with another's.
    kinds = _inline_types("Costs $5 and $6.\n\nAlso $ x $ here.\n\n`$code$`\n")
    assert not any(t.startswith("math") for t, _ in kinds)


def test_unclosed_display_math_does_not_swallow_the_document():
    tokens = PARSER.parse("$$\nunclosed\n\nnext para\n")
    assert not any(t.type == "math_block" for t in tokens)
    assert any(t.type == "inline" and t.content == "next para" for t in tokens)


def test_inline_text_keeps_math_source():
    heading = PARSER.parse("# The $\\pi$ *policy*\n")[1]
    assert inline_text(heading.children) == r"The \pi policy"


def test_inline_text_of_image_alt_keeps_math():
    inline = PARSER.parse("![cap $\\theta$ `x`](f.png)\n")[1]
    assert inline_text(inline.children) == r"cap \theta x"
```

In `tests/test_figures_refs.py` add:

```python
def test_figure_links_next_to_math_still_resolve():
    md = "Where $\\theta$ is learned:\n\n![policy $\\pi_\\theta$](figures/slide-004.png)\n"
    assert find_refs(md) == [4]
    assert find_malformed(md) == []
```

(Import `find_malformed` there if the file does not already.)

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_mdparse.py tests/test_figures_refs.py -v`
Expected: the new math tests FAIL (no math tokens; `inline_text` ImportError).

- [ ] **Step 4: Implement**

In `src/lecnotes/mdparse.py`:

```python
from mdit_py_plugins.dollarmath import dollarmath_plugin

_MATH_INLINE = ("math_inline", "math_inline_double")


def new_parser() -> MarkdownIt:
    """A fresh parser. Take one whenever you need to add render rules."""
    return (
        MarkdownIt("commonmark", {"html": False})
        .enable(["table", "strikethrough"])
        # $...$ and $$...$$ LaTeX. No spaces just inside the dollars and no digit
        # right after them, so prices like "$5 and $6" stay prose.
        .use(
            dollarmath_plugin,
            allow_labels=False,
            allow_space=False,
            allow_digits=False,
            double_inline=True,
        )
    )


def inline_text(children: list[Token]) -> str:
    """Plain text of inline tokens, keeping math as its LaTeX source.

    markdown-it's renderInlineAsText drops math tokens, which would turn
    "The $\\pi$ policy" into "The  policy" in titles and captions.
    """
    parts = []
    for token in children:
        if token.type in ("text", "code_inline", *_MATH_INLINE):
            parts.append(token.content)
        elif token.type == "image":
            parts.append(inline_text(token.children or []))
        elif token.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts)
```

Keep `PARSER = new_parser()` and `inline_tokens` unchanged.

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_mdparse.py tests/test_figures_refs.py -v` → PASS. Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/lecnotes/mdparse.py tests/test_mdparse.py tests/test_figures_refs.py
git commit   # subject: "Parse $...$ and $$...$$ LaTeX in the shared Markdown parser"
```

---

### Task 2: Instructions tell agents to write LaTeX

**Files:**
- Modify: `src/lecnotes/instructions.py`, `src/lecnotes/templates/instructions.md`
- Test: `tests/test_instructions.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `render_instructions(deck, slides, source_name) -> str` (signature unchanged)

- [ ] **Step 1: Update the tests first**

In `tests/test_instructions.py`, replace `test_no_unreplaced_placeholders` with:

```python
def test_no_unreplaced_placeholders():
    out = rendered()
    assert "{{" not in out and "}}" not in out


def test_equations_are_latex():
    out = rendered()
    assert "$\\pi_\\theta(a_t \\mid s_t)$" in out
    assert "\n    $$\n" in out
    assert "\\$" in out  # how to write a literal dollar
    assert "code spans" in out


def test_no_plain_text_equation_wording():
    assert "Type every equation as plain text" not in rendered()


def test_values_containing_braces_or_dollars_are_inserted_verbatim():
    out = rendered(deck="lec-{x}$", source_name="$deck{{slides}}.pdf")
    assert "lec-{x}$" in out
    assert "$deck{{slides}}.pdf" in out
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_instructions.py -v` → the new tests FAIL.

- [ ] **Step 3: Implement the loader**

Replace `src/lecnotes/instructions.py` with:

```python
"""Fill the agent-facing contract template.

Placeholders are {{name}}. The template teaches LaTeX, so it is full of dollar
signs; string.Template's $-placeholders would collide with them.
"""

import re
from importlib.resources import files

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def render_instructions(deck: str, slides: int, source_name: str) -> str:
    raw = files("lecnotes.templates").joinpath("instructions.md").read_text(encoding="utf-8")
    values = {"deck": deck, "slides": str(slides), "source_name": source_name}
    # One pass, so a value that itself contains "{{...}}" is never re-expanded.
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], raw)
```

- [ ] **Step 4: Update the template**

In `src/lecnotes/templates/instructions.md`: replace every `$deck` with `{{deck}}`, `$slides` with `{{slides}}`, `$source_name` with `{{source_name}}` (including the `out/$deck.md` at the end). Then replace the whole `### Equations` section (heading through the paragraph before `### Going beyond the slides`) with exactly:

```markdown
### Equations

Write math as LaTeX. Use `$...$` for math inside a sentence, and a display block
for an equation that stands on its own:

    The policy $\pi_\theta(a_t \mid s_t)$ maps states to action probabilities.

    $$
    \nabla_\theta J(\theta) = \mathbb{E}_{\tau \sim p_\theta}\left[\sum_t \nabla_\theta \log \pi_\theta(a_t \mid s_t)\, \hat{A}_t\right]
    $$

Put each `$$` on its own line, with a blank line before and after the block. No
space just inside the dollar signs (`$x$`, not `$ x $`). Write a literal dollar
sign as `\$`. Never use code spans or code blocks for math — keep those for code,
identifiers, commands, and file names.

Type every equation, including ones the slide shows only as an image, and define
the variables it uses. Do not link a slide as a figure just to show an equation.
```

Leave the rest of the template unchanged.

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_instructions.py tests/test_prep.py -v` → PASS. Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 6: Commit**

Subject: "Tell agents to write equations as LaTeX"

---

### Task 3: Vendor KaTeX

**Files:**
- Create: `src/lecnotes/vendor/__init__.py`, `src/lecnotes/vendor/katex/__init__.py` (both empty)
- Create: `src/lecnotes/vendor/katex/{katex.min.js,katex.min.css,LICENSE,VERSION,fonts/*.woff2}`
- Create: `src/lecnotes/katex.py`
- Test: `tests/test_katex.py`

**Interfaces:**
- Produces: `KATEX_VERSION = "0.18.7"`; `katex_css() -> str` (KaTeX CSS with every `@font-face` `src` a single WOFF2 data URI; cached); `katex_js() -> str` (cached)

- [ ] **Step 1: Fetch and verify KaTeX 0.18.7**

```bash
SCRATCH=/private/tmp/claude-501/-Users-jasonlai150-Documents-GitHub-4440/b8ce7be5-28b5-4a05-868b-6c0cf5495ca3/scratchpad
rm -rf "$SCRATCH/katex-vendor" && mkdir -p "$SCRATCH/katex-vendor" && cd "$SCRATCH/katex-vendor"
curl -sL https://registry.npmjs.org/katex/0.18.7 -o meta.json
curl -sL https://registry.npmjs.org/katex/-/katex-0.18.7.tgz -o katex.tgz
python3 - <<'EOF'
import base64, hashlib, json
meta = json.load(open("meta.json"))
algo, digest = meta["dist"]["integrity"].split("-", 1)
actual = base64.b64encode(hashlib.new(algo, open("katex.tgz", "rb").read()).digest()).decode()
assert actual == digest, "integrity mismatch"
print("integrity ok", algo)
EOF
tar -xzf katex.tgz
DEST=/Users/jasonlai150/Documents/GitHub/lecnotes/src/lecnotes/vendor/katex
mkdir -p "$DEST/fonts"
cp package/dist/katex.min.js package/dist/katex.min.css package/LICENSE "$DEST/"
cp package/dist/fonts/*.woff2 "$DEST/fonts/"
printf '0.18.7\n' > "$DEST/VERSION"
ls "$DEST/fonts" | wc -l   # expect 20
```

Stop and report BLOCKED if the integrity check fails.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_katex.py`:

```python
import re
from importlib.resources import files

from lecnotes.katex import KATEX_VERSION, katex_css, katex_js


def test_version_matches_vendored_file():
    vendored = files("lecnotes.vendor.katex").joinpath("VERSION").read_text().strip()
    assert KATEX_VERSION == vendored == "0.18.7"


def test_every_font_face_is_an_inlined_woff2():
    css = katex_css()
    faces = re.findall(r"@font-face\{[^}]*\}", css)
    assert len(faces) == 20
    for face in faces:
        assert 'src:url(data:font/woff2;base64,' in face
        assert face.count("url(") == 1
    assert "url(fonts/" not in css
    assert ".woff)" not in css and ".ttf)" not in css


def test_css_keeps_katex_rules():
    assert ".katex{" in katex_css() or ".katex {" in katex_css()


def test_js_is_safe_to_inline_in_a_script_tag():
    js = katex_js()
    assert "katex" in js
    assert "</script" not in js.lower()
    assert "<!--" not in js


def test_assets_are_cached():
    assert katex_css() is katex_css()
    assert katex_js() is katex_js()


def test_license_is_vendored():
    assert "MIT" in files("lecnotes.vendor.katex").joinpath("LICENSE").read_text()
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_katex.py -v` → FAIL (`ModuleNotFoundError: lecnotes.katex`).

- [ ] **Step 4: Implement**

Create `src/lecnotes/katex.py`:

```python
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
```

- [ ] **Step 5: Run tests and confirm packaging**

Run: `uv run pytest tests/test_katex.py -v` → PASS. Then `uv run pytest -q` → all pass, no warnings.
Run: `uv build --wheel -o "$SCRATCH/wheel" && unzip -l "$SCRATCH/wheel"/*.whl | grep -c 'vendor/katex/fonts/.*woff2'` → `20`.

- [ ] **Step 6: Commit**

```bash
git add src/lecnotes/vendor src/lecnotes/katex.py tests/test_katex.py
```
Subject: "Vendor KaTeX 0.18.7 for rendering math in HTML exports"

---

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

### Task 5: Notion math passthrough, titles, README

**Files:**
- Modify: `src/lecnotes/export_notion.py`, `README.md`, `docs/BACKLOG.md`
- Test: `tests/test_export_notion.py`

**Interfaces:**
- Consumes: `mdparse.inline_text`
- Produces: nothing new

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_export_notion.py`:

```python
def test_math_passes_through_unwrap_unchanged():
    md = (
        "Policy $\\pi_\\theta(a_t \\mid s_t)$ acts\nhere.\n\n"
        "$$\n\\nabla_\\theta J(\\theta) =\n\\mathbb{E}[x]\n$$\n"
    )
    out = unwrap(md)
    assert "Policy $\\pi_\\theta(a_t \\mid s_t)$ acts here." in out
    assert "$$\n\\nabla_\\theta J(\\theta) =\n\\mathbb{E}[x]\n$$\n" in out


def test_title_keeps_math_source():
    # Math survives as its LaTeX source; the backslash is then an unsafe filename
    # character and becomes "-" like any other.
    stem, body = split_title("# The $\\pi$ policy\n\ntext\n", "lec1")
    assert stem == "The -pi policy"
    assert body == "text\n"


def test_math_is_byte_identical_in_the_zip(tmp_path):
    md = "# T\n\nInline $a_i * b_j$.\n\n$$\n\\sum_t r_t\n$$\n"
    dest = tmp_path / "t.zip"
    write_notion_zip(md, [], tmp_path, dest, "t")
    with zipfile.ZipFile(dest) as zf:
        text = zf.read("T.md").decode("utf-8")
    assert "Inline $a_i * b_j$." in text
    assert "$$\n\\sum_t r_t\n$$\n" in text
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_export_notion.py -v` → `test_title_keeps_math_source` FAILS (math dropped today, giving `The policy`).

- [ ] **Step 3: Implement**

In `src/lecnotes/export_notion.py`: import `inline_text` from `.mdparse` alongside `PARSER`, and in `split_title` replace the `PARSER.renderer.renderInlineAsText(...)` call with `inline_text(tokens[i + 1].children or [])`.

- [ ] **Step 4: README and backlog**

README: in the Export section, add one paragraph after the HTML bullet list:

```markdown
Equations are written as LaTeX (`$...$` inline, `$$` blocks), which VS Code,
GitHub and Obsidian preview directly. The HTML export renders them with a copy of
KaTeX embedded in the file (added only when the notes contain math, about 0.7 MB);
the Notion zip passes them through unchanged.
```

`docs/BACKLOG.md`: in "Not yet verified in real use", extend the Notion bullet with: "and how the importer treats `$...$` inline math and `$$` blocks". In "Features", replace the "Math rendering (in progress…)" entry with a one-line "Math rendering: done (LaTeX + KaTeX in HTML, passthrough to Notion)." — or remove it; keep the Observability entry unchanged.

- [ ] **Step 5: Run tests**

Run: `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 6: Commit**

Subject: "Keep math in Notion titles; document LaTeX math"
(stage `src/lecnotes/export_notion.py tests/test_export_notion.py README.md docs/BACKLOG.md`)

---

## After the plan (controller)

Regenerate CS 8803 DRL lectures 2 and 3 (`DRL lectures/draft-lec-2-…notes`, `draft-lec-3-…notes`): back up `NOTES.md` to `NOTES.before-latex.md`, `lecnotes prep <pdf> --force`, a fresh writing agent per lecture pointed only at `INSTRUCTIONS.md`, then `finish` and `export --to html` / `--to notion`. Report words, figures, LaTeX expressions, and agent feedback.

## Verification

- [ ] `uv run pytest -q` passes, no warnings
- [ ] A math-free export has no `<script>`; a math export renders in a browser with KaTeX
- [ ] The wheel contains the 20 KaTeX fonts
