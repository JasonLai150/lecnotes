# Fix report: figure links silently dropped by `finish`

## Summary

`find_refs`/`find_malformed` in `src/lecnotes/figures.py` used to scan NOTES.md
with regexes (`REF_RE`/`IMAGE_RE`, both `[^\]]*` for the caption). A caption
containing `]` broke the match entirely, so `find_refs` never saw the link and
`finish` silently dropped the figure while still returning `ok: true`. Fixed
by replacing the regex scan with a `markdown-it-py` parse, per the brief.

## What changed

- `pyproject.toml:6-9`, `uv.lock` — added runtime dependency `markdown-it-py>=3`
  (resolved `markdown-it-py==4.2.0`, plus transitive `mdurl`).
- `src/lecnotes/figures.py`
  - Removed `REF_RE`, `IMAGE_RE`, `SLIDE_PNG_RE` (regex-based, line-blind to
    Markdown structure).
  - Added `STRICT_SRC_RE` (figures.py:76, the exact `figures/slide-NNN.png`
    form), `SLIDE_PNG_RE` (figures.py:81, loose "looks like a slide path"
    check), `LOOSE_TEXT_RE` (figures.py:86, pulls the offending fragment out
    of failed-to-parse markup or prose).
  - Added a shared `_MD = MarkdownIt("commonmark", {"html": False})` instance
    (figures.py:91) and `_iter_link_tokens()` (figures.py:94-108), a generator
    yielding only `image`/`link_open`/`text` inline tokens in document order —
    `code_inline`/`fence`/`code_block` tokens are structurally excluded since
    they never appear in that set, so code spans and fenced blocks are never
    scanned.
  - `find_refs()` (figures.py:111-121): walks `image` tokens, checks `src`
    against `STRICT_SRC_RE.fullmatch`, returns sorted de-duped slide numbers.
  - `find_malformed()` (figures.py:124-147): walks tokens and reports, in
    document order, de-duplicated:
    a. `image` src containing the slide-path shape but not the exact form
    b. `link_open` href containing the slide-path shape (missing `!`)
    c. `text` content matching `\S*slide-\d+\.png\S*` (markup that failed to
       parse as a link at all, or a bare filename mention)
- `src/lecnotes/commands.py:115-123` — `figure_malformed` error message now
  also states the usual causes: "an unbalanced [ or ] in the caption, a
  missing !, or a path other than figures/slide-NNN.png."
- `src/lecnotes/templates/instructions.md:43-44` — removed the "no link
  title" clause; link titles are now valid.
- `tests/test_figures_refs.py` — new tests for every brief scenario (see
  RED/GREEN below); updated the title-case malformed test (now valid, per
  brief item 2) and two other pre-existing "not malformed" cases that
  conflict with the brief's own (intentionally broader) rules (see
  Deviations).
- `tests/test_finish.py` — two new tests: a bracketed caption resolves
  (`test_bracket_in_caption_does_not_drop_the_figure`), an unbalanced-bracket
  caption is rejected as `figure_malformed`
  (`test_unbalanced_bracket_in_caption_is_malformed`).

## TDD evidence

### RED (new tests, before touching figures.py/commands.py)

Ran `uv run pytest tests/test_figures_refs.py tests/test_finish.py -q` after
writing the new tests against the still-regex-based implementation:

```
FAILED tests/test_figures_refs.py::test_well_formed_and_unrelated_links_are_not_malformed[![t](figures/slide-001.png "title")]
FAILED tests/test_figures_refs.py::test_bracket_in_caption_still_resolves_as_a_ref
FAILED tests/test_figures_refs.py::test_unbalanced_bracket_in_caption_is_malformed_not_dropped
FAILED tests/test_figures_refs.py::test_missing_bang_is_malformed
FAILED tests/test_figures_refs.py::test_code_spans_and_fenced_blocks_are_not_scanned
FAILED tests/test_figures_refs.py::test_link_title_is_valid
FAILED tests/test_finish.py::test_bracket_in_caption_does_not_drop_the_figure
FAILED tests/test_finish.py::test_unbalanced_bracket_in_caption_is_malformed
8 failed, 36 passed in 1.58s
```

Each failure was for the expected reason, e.g.
`test_bracket_in_caption_does_not_drop_the_figure` failed with
`assert 0 == 1` (the figure was dropped, exactly the reported bug), and
`test_bracket_in_caption_still_resolves_as_a_ref` failed with `assert [] ==
[19]` (find_refs missed the bracketed-caption ref entirely).

### GREEN (after implementing the markdown-it-py parse)

```
uv run pytest tests/test_figures_refs.py -q  ->  27 passed
uv run pytest tests/test_finish.py -q        ->  17 passed
```

## Full suite

```
uv run pytest -q
184 passed in 3.90s
```

(Baseline before this work: `177 passed`. Net +7 tests: 5 new in
test_figures_refs.py's standalone tests, minus 1 net from parametrize-list
edits, plus 2 more standalone additions there, plus 2 new in test_finish.py —
see commit for exact diff.) No warnings were emitted (pytest prints no
warnings summary section when none occur, and none did).

## Deviations from the brief

1. **Indented test fixtures became CommonMark code blocks.** Two pre-existing
   tests (`test_sorts_and_dedupes`, originally
   `test_malformed_targets_are_in_document_order_and_deduplicated`) built
   their markdown as a triple-quoted string with each line indented 4 spaces
   (matching the surrounding Python indentation). Under real CommonMark
   parsing, 4+ leading spaces make a line part of an **indented code block**,
   not a paragraph — so `markdown-it-py` correctly, but unhelpfully for these
   fixtures, treated the image lines as code and produced no inline
   image/link tokens at all. `find_refs`/`find_malformed` returned `[]` for
   both, failing the tests. This isn't a real link ever being dropped (no
   NOTES.md a person writes would indent plain prose links this way) — it's
   an artifact of how the old regex-based tests were authored, since the old
   regex was blind to Markdown structure. Smallest fix: left-align the
   fixture strings (flush against column 0) so they parse as ordinary
   paragraphs, preserving the tests' actual intent (sort+dedupe of refs,
   order+dedupe of malformed targets) unchanged. See
   `tests/test_figures_refs.py::test_sorts_and_dedupes` and
   `::test_malformed_targets_are_in_document_order_and_deduplicated`.

2. **Two pre-existing "not malformed" cases now correctly report as
   malformed, per the brief's own rules.** `test_well_formed_and_unrelated_links_are_not_malformed`
   included `"prose mentioning pages/slide-002.png without an image"` and
   `"[a plain link](pages/slide-002.png)"`, both asserting `find_malformed ==
   []`. The brief's rule (b) ("`link_open` tokens whose `href` contains
   `slide-\d+\.png`") and rule (c) ("`text` tokens containing
   `slide-\d+\.png` ... or a bare filename in prose") are both written
   directory-agnostic and intent-agnostic by design — the brief explicitly
   names "a bare filename in prose" as one of the two causes of a matching
   `text` token, in the same breath as "link markup that failed to parse",
   because the parser cannot tell those two apart. Implementing those rules
   literally (as instructed) makes both of these old cases malformed now.
   I judged this as the brief's own intentional broadening (not a parser
   quirk), so I updated the tests rather than narrowing the implementation:
   removed both from the "not malformed" list and added
   `test_bare_filename_mention_in_prose_is_reported` and
   `test_plain_link_missing_the_bang_is_reported_regardless_of_directory`
   asserting the new (correct, per brief) malformed result. Flagging this
   explicitly in case the broadened scope (prose mentions can now trip
   `figure_malformed`) is not what was wanted — it was the literal reading of
   rule (c)'s own parenthetical.

No other assumption in the brief needed adjusting: the "missing `!`",
"unbalanced `[`", code-span/fence exclusion, and link-title cases all behave
exactly as the brief describes once parsed for real (verified interactively
with `MarkdownIt("commonmark", {"html": False}).parse(...)` against each
brief example before writing the implementation).

## Commits

- `69f07a9` — Add markdown-it-py runtime dependency
- `36e5491` — Fix finish silently dropping figure links with bracketed captions

Not pushed. Nothing under `docs/superpowers/sdd/` was staged or committed.
