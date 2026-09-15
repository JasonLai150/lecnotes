# Task 5 report: Notion math passthrough, titles, README (+ Task 2 review fix)

## What I implemented

### Task 5 proper

- `src/lecnotes/export_notion.py`: imported `inline_text` alongside `PARSER` from
  `.mdparse`, and in `split_title` replaced the
  `PARSER.renderer.renderInlineAsText(tokens[i + 1].children or [], PARSER.options, {})`
  call with `inline_text(tokens[i + 1].children or [])`. `renderInlineAsText` has no
  handling for the `math_inline`/`math_inline_double` token types added in Task 1 and
  silently drops their content, so an H1 like `# The $\pi$ policy` was titling the
  Notion page "The policy". `unwrap` and `write_notion_zip` needed no change — math
  dollar syntax already passed through them unchanged, since neither one re-renders
  Markdown, only joins hard-wrapped paragraph lines and writes bytes to a zip.
- `README.md`: added the brief's paragraph verbatim to the Export section, after the
  HTML/Notion bullet list, describing LaTeX math source, VS Code/GitHub/Obsidian
  preview, KaTeX in the HTML export (conditional, ~0.7 MB), and Notion passthrough.
- `docs/BACKLOG.md`: replaced the "Math rendering (in progress, 2026-09-15)" Features
  entry with the one-line "Math rendering: done (LaTeX + KaTeX in HTML, passthrough to
  Notion)."; extended the "Notion import" bullet under "Not yet verified in real use"
  with "and how the importer treats `$...$` inline math and `$$` blocks."; left the
  Observability entry unchanged.

### Folded-in Task 2 review fix

Task 2's review found that the Equations example in
`src/lecnotes/templates/instructions.md` is indented 4 spaces (to mark it as an
example within the instructions prose), and an agent copying that indentation
literally into `NOTES.md` would produce a 4-space-indented `$$` block — which
CommonMark treats as an indented code block, not a paragraph/math construct, so the
equation renders as raw LaTeX text with no error or warning.

- Changed the sentence "Put each `` `$$` `` on its own line, with a blank line before
  and after the block." to "Put each `` `$$` `` on its own line, flush left with no
  indentation (the indentation above only marks the example), with a blank line before
  and after the block." — exact wording from the brief, backticks kept only around
  `$$` as in the original sentence.
- Added `test_display_math_must_be_flush_left` to `tests/test_instructions.py`.
- Added `test_indented_display_math_is_a_code_block_not_math` to `tests/test_mdparse.py`,
  documenting (rather than changing) why the rule exists: parsing a 4-space-indented
  `$$` block with `PARSER` already yields a `code_block` token, not `math_block` —
  this was CommonMark's existing indented-code-block precedence, untouched by the
  dollarmath plugin.

## TDD evidence

### RED

Command: `uv run pytest tests/test_export_notion.py -v -k "math_passes_through_unwrap_unchanged or title_keeps_math_source or math_is_byte_identical_in_the_zip"`
(after appending the three tests from the brief, before touching `export_notion.py`):

```
tests/test_export_notion.py::test_math_passes_through_unwrap_unchanged PASSED
tests/test_export_notion.py::test_title_keeps_math_source FAILED
tests/test_export_notion.py::test_math_is_byte_identical_in_the_zip PASSED

FAILED tests/test_export_notion.py::test_title_keeps_math_source - AssertionError:
assert 'The policy' == 'The -pi policy'
```

This is the exact failure the brief predicted ("math dropped today, giving `The
policy`"). The other two tests passed immediately because `unwrap`/`write_notion_zip`
never re-render Markdown; only `split_title`'s title extraction needed the fix.

Command: `uv run pytest tests/test_instructions.py -v -k flush_left` (after appending
`test_display_math_must_be_flush_left`, before editing the template):

```
tests/test_instructions.py::test_display_math_must_be_flush_left FAILED
AssertionError: assert 'flush left' in "# Write the notes for `lec1`\n\n..."
```

Expected: the wording didn't exist yet in the template.

Command: `uv run pytest tests/test_mdparse.py -v -k indented_display_math` (after
appending `test_indented_display_math_is_a_code_block_not_math`):

```
tests/test_mdparse.py::test_indented_display_math_is_a_code_block_not_math PASSED
```

This one passed immediately — it documents existing parser behavior (CommonMark's
indented-code-block rule pre-empting the dollarmath plugin) rather than driving a code
change; the brief describes it as documentation ("documents why the rule exists"), not
a RED-first assertion.

### GREEN

Implemented the `export_notion.py` change and the template wording change per the
brief.

Command: `uv run pytest tests/test_export_notion.py -v` → `23 passed in 0.13s` (20
pre-existing + 3 new).

Command: `uv run pytest tests/test_instructions.py -v` → `16 passed in 0.01s` (15
pre-existing + 1 new).

Command: `uv run pytest tests/test_mdparse.py -v` → all pass, including the new
documentation test.

Full suite: `uv run pytest -q` → `319 passed in 5.05s`, no warnings.

## Files changed

- `src/lecnotes/export_notion.py` — `inline_text` import and use in `split_title`.
- `tests/test_export_notion.py` — 3 new tests appended verbatim from the brief.
- `README.md` — one new paragraph in the Export section, verbatim from the brief.
- `docs/BACKLOG.md` — Math rendering entry marked done; Notion "not yet verified"
  bullet extended.
- `src/lecnotes/templates/instructions.md` — "flush left with no indentation" wording
  added to the Equations section, verbatim from the brief.
- `tests/test_instructions.py` — 1 new test (`test_display_math_must_be_flush_left`).
- `tests/test_mdparse.py` — 1 new test (`test_indented_display_math_is_a_code_block_not_math`).

Not committed: `docs/superpowers/sdd/2026-09-15-lecnotes-math/progress.md` and
`task-5-brief.md`, which were already modified in the working tree before I started
(by the controller) — instructions say never to commit anything under `docs/superpowers/sdd/`.

## Deviations from the brief

None. Every code/doc change matches the brief's snippets verbatim; no assumption in
the brief (parser API, `inline_text` signature, existing sentence text to match)
needed adjustment.

## Self-review findings

Read the diff with fresh eyes:

- Completeness: both halves of the brief (Task 5 proper + the folded-in Task 2 fix)
  are present — `export_notion.py`, README, BACKLOG, plus the template wording and its
  two documenting tests.
- Quality: the `split_title` change is a straight one-line swap consistent with the
  identical fix already made to `export_html.py` in Task 4 (same `inline_text` import
  pattern, same reasoning).
- Discipline: nothing extra added; `unwrap`/`write_notion_zip` were left untouched
  since they didn't need to change (verified by the RED run — those two tests passed
  before any implementation).
- Testing: all 6 new tests exercise real behavior end to end, no mocking; confirmed
  `test_split_title_strips_inline_markup`, `test_split_title_falls_back_without_h1`,
  and the other pre-existing `split_title`/`sanitize_filename` tests still pass
  unchanged after the swap.

No issues found; nothing fixed post-review.

## Concerns

None. Per the brief, this task does not touch `src/lecnotes/vendor/`,
`src/lecnotes/katex.py`, or `export_html.py` — those are Task 3/4's files and were
left alone. The Verification checklist items about KaTeX fonts/wheel/HTML `<script>`
behavior belong to Task 4, not this task, and were not re-verified here.

## Test summary

Before this task: 314 passed. After: 319 passed (6 new tests), no warnings.
