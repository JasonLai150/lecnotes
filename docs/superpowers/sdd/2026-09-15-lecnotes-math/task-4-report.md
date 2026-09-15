# Task 4 report: Render math in the HTML export

## What I implemented

`src/lecnotes/export_html.py` now renders `math_inline`, `math_inline_double`, and
`math_block` tokens produced by `mdparse.new_parser()` (Task 1) as KaTeX-ready markup,
and inlines the vendored KaTeX CSS/JS (Task 3, via `lecnotes.katex.katex_css()` /
`katex_js()`) only into pages that actually contain math:

- Added `_MATH_CSS` (display-math layout: block, margin, horizontal scroll for wide
  formulas) and `_RENDER_MATH` (the client-side script that calls `katex.render` on
  every `.lecnotes-math` element, with `throwOnError: false` and `trust: false`).
- Added `_math_inline` render rule: `<span class="lecnotes-math">{escaped latex}</span>`.
- Added `_math_display` render rule (shared by `math_inline_double` and `math_block`):
  `<div class="lecnotes-math lecnotes-math-display">{escaped, stripped latex}</div>`.
  Stripping normalizes `$$\n...\n$$` blocks and `$$...$$` inline-double math to the
  same rendered markup.
- Registered all three render rules on the parser inside `render_html`, alongside the
  existing `paragraph_open`/`paragraph_close` figure rules.
- Added a `has_math` flag, set while walking tokens (checking both the token itself and
  its inline children for the three math token types), and used it to conditionally
  emit a `<style>` block (KaTeX CSS + `_MATH_CSS`) in `<head>` and two `<script>` blocks
  (KaTeX JS + the render script) before `</body>` — so a page with no math still has
  zero `<script>` tags, per `global-constraints.md`.
- Replaced both `md.renderer.renderInlineAsText(...)` calls (title from the first H1,
  figure caption) with `inline_text(...)` from `mdparse` (Task 1), so a title or
  caption containing math keeps the LaTeX source instead of losing it — `renderInlineAsText`
  has no handling for the new math token types and drops their content.
- Added the two new imports (`from .katex import katex_css, katex_js`,
  `from .mdparse import inline_text, new_parser`).

## TDD evidence

### RED

Command: `uv run pytest tests/test_export_html.py -v`

Appended the six tests from the brief (`test_inline_math_is_escaped_latex_in_a_span`,
`test_display_math_uses_a_display_div`, `test_katex_is_inlined_only_with_math`,
`test_math_page_makes_no_external_loads`, `test_title_and_caption_keep_math_source`,
`test_math_in_code_is_code`) to `tests/test_export_html.py` before touching
`export_html.py`. Result: 4 failed, 17 passed (`test_math_page_makes_no_external_loads`
and `test_math_in_code_is_code` passed trivially since nothing math-related existed yet
to violate them).

Representative failures, all for the expected reason (no math render rules, no KaTeX
inlining, `renderInlineAsText` dropping math content):

```
tests/test_export_html.py::test_inline_math_is_escaped_latex_in_a_span FAILED
  assert '<span class="lecnotes-math">a&lt;b</span>' in html
  ... actual body had '<span class="math inline">a&lt;b</span>' (markdown-it-py's
  default dollarmath rendering, no lecnotes-math class)

tests/test_export_html.py::test_display_math_uses_a_display_div FAILED
  assert '<div class="lecnotes-math lecnotes-math-display">x^2</div>' in html
  ... actual body had '<div class="math inline">x^2</div>' for $$x^2$$

tests/test_export_html.py::test_katex_is_inlined_only_with_math FAILED
  assert katex_js() in with_math  -- KaTeX JS never inlined

tests/test_export_html.py::test_title_and_caption_keep_math_source FAILED
  assert '<title>The \\pi policy</title>' in html
  ... actual title was '<title>The  policy</title>' (renderInlineAsText drops math)
```

Full run: `4 failed, 17 passed in 0.17s`.

### GREEN

Implemented `export_html.py` per the brief's Step 3 exactly (render rules, `has_math`
tracking, conditional KaTeX inlining, `inline_text` for title/caption).

Command: `uv run pytest tests/test_export_html.py -v` → `21 passed in 0.15s` (all 15
pre-existing tests plus the 6 new ones).

Full suite: `uv run pytest -q` → `314 passed in 4.98s`, no warnings.

## Files changed

- `src/lecnotes/export_html.py` — math render rules, conditional KaTeX inlining,
  `inline_text` for title/caption (see diff for exact lines).
- `tests/test_export_html.py` — six new tests appended verbatim from the brief.

## Deviations from the brief

None. The brief's code snippets were used verbatim; no assumption in the brief
(parser API, `_data_uri` signature, `add_render_rule` signature, `inline_text`
signature, `katex_css`/`katex_js` signatures) needed adjustment.

## Self-review findings

Read the diff with fresh eyes:

- Completeness: all three math token types get render rules; both math-bearing-title
  and math-bearing-caption paths use `inline_text`; `has_math` checks both the token
  itself (for `math_block`, which is a top-level block token) and its children (for
  `math_inline`/`math_inline_double`, which live inside `inline` tokens) — confirmed
  by `test_display_math_uses_a_display_div` covering both a block-form and
  double-dollar-inline-form `$$...$$`.
- Quality: names (`_math_inline`, `_math_display`, `has_math`, `head_math`,
  `body_math`) match the surrounding style; no duplication introduced (`_math_display`
  is reused for both `math_inline_double` and `math_block` since their rendering is
  identical per the brief).
- Discipline: nothing added beyond the brief's Step 3; no speculative options or config
  surfaced (e.g. did not parameterize KaTeX options, did not add a way to opt out of
  math rendering — none was asked for).
- Testing: all six new tests exercise real `render_html` output end to end (no
  mocking); confirmed the RED run failed for the documented reasons before
  implementing, and confirmed `test_page_shell_is_self_contained` (no math in its
  document) still passes unchanged.

No issues found; nothing fixed post-review.

## Concerns

None.

## Test summary

Before this task: 308 passed. After: 314 passed (6 new tests), no warnings.

---

## Fix round 1 (review findings)

The review verified rendering in headless Chrome and raised two Important issues.
Both fixed in one commit, test-first.

### Finding 1: `math_inline_double` as `<div>` breaks paragraph HTML mid-paragraph

Root cause: `math_inline_double` (`$$...$$` used inline, e.g. "Inline $$x^2$$ here.")
is an *inline* token — markdown-it-py can place it inside a `<p>`. Rendering it as a
`<div>` (as `_math_display` did, shared with the block-level `math_block`) produces
invalid HTML: `<p>Inline <span>...</span> and <div>...</div> here.</p>`. A browser's
HTML5 parser auto-closes `<p>` on hitting the `<div>`, orphaning the trailing text
under `<body>` and inserting a spurious empty `<p></p>`.

Fix (controller-mandated): split the old shared `_math_display` render rule into two —
`_math_inline_display` for `math_inline_double`, rendering
`<span class="lecnotes-math lecnotes-math-display">{escaped, stripped latex}</span>`,
and `_math_block` for `math_block`, keeping the `<div class="lecnotes-math
lecnotes-math-display">`. `_MATH_CSS`'s `.lecnotes-math-display { display: block; ... }`
already applies to a `<span>`, and `_RENDER_MATH`'s `displayMode` check reads the class,
not the tag, so no other code needed to change.

**RED** — `uv run pytest tests/test_mdparse.py tests/test_export_html.py -v`:

Updated `test_display_math_uses_a_display_div`'s `$$x^2$$` assertion from the `<div>`
form to the `<span>` form, and added `test_double_dollar_mid_paragraph_stays_inline_html`
(asserts the exact paragraph string `<p>Inline <span class="lecnotes-math
lecnotes-math-display">x^2</span> here.</p>` and that no `<div` appears anywhere, since
this document has no `math_block`). Both failed before the fix:

```
tests/test_export_html.py::test_display_math_uses_a_display_div FAILED
  assert '<span class="lecnotes-math lecnotes-math-display">x^2</span>' in html
  ... actual output still had '<div class="lecnotes-math lecnotes-math-display">x^2</div>'

tests/test_export_html.py::test_double_dollar_mid_paragraph_stays_inline_html FAILED
  assert '<p>Inline <span class="lecnotes-math lecnotes-math-display">x^2</span> here.</p>' in html
  ... actual output had the div form breaking the paragraph
```

**GREEN** — after splitting the render rule and updating the registration
(`md.add_render_rule("math_inline_double", _math_inline_display)`,
`md.add_render_rule("math_block", _math_block)`), both tests passed.

### Finding 2: blockquote markers leak into `math_block` content

Root cause: markdown-it's block parser strips each line's leading `> ` before handing
block rules their content, but `mdit_py_plugins.dollarmath`'s display-math rule reads
raw source lines directly (a known quirk of that plugin), so a `math_block` token
nested inside a blockquote keeps the `> ` prefix on every line of `.content`.
Confirmed before fixing:
`new_parser().parse("> text\n>\n> $$\n> \\nabla_\\theta J(\\theta)\n> $$\n")` produced
a `math_block` token with `.content == '\n> \\nabla_\\theta J(\\theta)\n> '` — KaTeX
would render the literal `>` characters as part of the formula.

Fix (controller-mandated): in `src/lecnotes/mdparse.py`, added a private core rule
`_strip_blockquote_markers(state: StateCore)`, registered via
`md.core.ruler.after("block", "lecnotes_math_in_blockquote", _strip_blockquote_markers)`
inside `new_parser()` (so the module-level `PARSER` picks it up automatically, since
it's built by calling `new_parser()`). The rule walks `state.tokens`, tracks blockquote
nesting depth via `blockquote_open`/`blockquote_close` counts, and for each `math_block`
token at depth `d > 0` strips, from the start of every line, up to `d` occurrences of
`_BLOCKQUOTE_MARKER = re.compile(r"^[ ]{0,3}>[ ]?")` — stopping early per line if fewer
than `d` markers are actually present, so a `>` the LaTeX source itself uses (not at the
very start of a line) is left untouched.

**RED** — `uv run pytest tests/test_mdparse.py -v`:

Added four tests to `tests/test_mdparse.py`:
`test_display_math_in_blockquote_strips_the_quote_marker` (single blockquote, asserts
`.content.strip() == r"\nabla_\theta J(\theta)"` and no line starts with `>`),
`test_display_math_in_nested_blockquote_strips_both_markers` (`> > $$\n> > x^2\n> > $$\n`
→ `x^2`), `test_display_math_gt_inside_the_latex_is_kept` (`> $$\n> a > b\n> $$\n` →
`a > b`, proving only the leading marker is stripped), and
`test_top_level_display_math_is_unaffected_by_the_blockquote_fix` (a bare `$$...$$`
block, unaffected). The first three failed before the fix:

```
tests/test_mdparse.py::test_display_math_in_blockquote_strips_the_quote_marker FAILED
  assert blocks[0].content.strip() == r"\nabla_\theta J(\theta)"
  AssertionError: assert '> \\nabla_\\theta J(\\theta)\n>' == '\\nabla_\\theta J(\\theta)'

tests/test_mdparse.py::test_display_math_in_nested_blockquote_strips_both_markers FAILED
  AssertionError: assert '> > x^2\n> >' == 'x^2'

tests/test_mdparse.py::test_display_math_gt_inside_the_latex_is_kept FAILED
  AssertionError: assert '> a > b\n>' == 'a > b'
```

Also added `test_display_math_in_blockquote_has_no_stray_quote_marker` to
`tests/test_export_html.py`: asserts the exact `<div class="lecnotes-math
lecnotes-math-display">\nabla_\theta J(\theta)</div>` appears, and that the rendered
*document body* (the HTML between `<body>\n` and the first `<script>` tag — scoped to
exclude the vendored KaTeX JS, which legitimately contains the literal string `"&gt;"`
in its own HTML-escaping table, an unrelated false positive I hit and fixed by narrowing
the assertion) contains no `&gt;`. This failed before the fix (the div's content had a
stray `> ` prefix, so the exact-string assertion did not match).

**GREEN** — after adding `_strip_blockquote_markers` and wiring it into `new_parser()`,
all four `test_mdparse.py` additions and the `test_export_html.py` addition passed.

### Covering test run

`uv run pytest tests/test_mdparse.py tests/test_export_html.py -v` → `40 passed in
0.16s` (12 new tests: 4 in `test_mdparse.py`, 1 new + 1 changed assertion + 4 more in
`test_export_html.py` — 6 total new/changed in that file, matching the ruling's list).

### Full suite

`uv run pytest -q` → `325 passed in 4.81s`, no warnings. (319 passed before this fix
round, reflecting Task 5's additions landing on top of this task's commit in the
interim; 325 after, i.e. 6 new tests from this fix round.)

### Files changed (this fix round)

- `src/lecnotes/export_html.py` — split `_math_display` into `_math_inline_display`
  (span) and `_math_block` (div); updated the `math_inline_double`/`math_block`
  render-rule registrations.
- `src/lecnotes/mdparse.py` — added `_BLOCKQUOTE_MARKER`, `_strip_blockquote_markers`,
  and wired it into `new_parser()` via `md.core.ruler.after("block", ...)`.
- `tests/test_export_html.py` — updated `test_display_math_uses_a_display_div`; added
  `test_double_dollar_mid_paragraph_stays_inline_html` and
  `test_display_math_in_blockquote_has_no_stray_quote_marker`.
- `tests/test_mdparse.py` — added four blockquote/math tests.

### Deviations from the ruling

One: the controller's exact test wording for Finding 2's HTML test was "with no `&gt;`
in it," referring to the rendered `<div>`. A literal whole-page `assert "&gt;" not in
html` is a false positive: the vendored KaTeX JS (unrelated to this bug) contains the
JS string literal `"&gt;"` as part of its own escaping table. I scoped the assertion to
the rendered document body (before the first `<script>` tag) rather than the whole
page, which preserves the intent (no stray blockquote marker leaks into the rendered
math) without failing on an unrelated, correct artifact of the vendored library.

### Self-review findings

- Confirmed `_RENDER_MATH`'s `displayMode: el.classList.contains("lecnotes-math-display")`
  needed no change, since it reads the class list, not the tag name — verified by
  `test_katex_is_inlined_only_with_math` and the KaTeX-related tests still passing
  unchanged.
- Confirmed the blockquote-marker fix only touches `math_block` tokens at depth > 0
  (checked via `test_top_level_display_math_is_unaffected_by_the_blockquote_fix`), and
  that it's registered inside `new_parser()` so both the shared module-level `PARSER`
  and every exporter's fresh parser instance get it consistently — no separate wiring
  needed in `export_html.py` or `export_notion.py`.
- Confirmed the depth-counting loop only inspects `blockquote_open`/`blockquote_close`
  and `math_block` token types, leaving every other token untouched, and that stripping
  stops early per line once fewer than `depth` markers remain (verified by the
  "`a > b`" test, which needs exactly one strip per line despite `depth == 1` allowing
  one attempt only — and by the nested test, which needs exactly two).
- Re-ran the full suite once more after both fixes together (not just each fix in
  isolation) to catch any interaction; none found.

### Concerns

None.

### Fix-round test summary

Before this fix round: 319 passed (reflects Task 5 landing after this task's original
commit). After: 325 passed (6 new tests), no warnings.
