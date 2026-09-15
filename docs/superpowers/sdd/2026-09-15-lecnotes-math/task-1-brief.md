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

