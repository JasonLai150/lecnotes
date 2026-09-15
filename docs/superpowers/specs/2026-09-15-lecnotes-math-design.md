# lecnotes math — design

**Date:** 2026-09-15
**Status:** approved design
**Extends:** `2026-08-27-lecnotes-design.md` and `2026-09-15-lecnotes-export-design.md` (with their amendments)

## Problem

Agents write equations as code spans — `` `V^π(s)` ``, `` `r(τ) = Σ_t r(s_t, a_t)` `` —
which read poorly in the Markdown and in every export.

## Decision

Math is written as LaTeX in the Markdown and rendered wherever the notes are read. This
applies to notes written from now on; existing notes are not converted (lectures 2 and 3
of CS 8803 DRL are regenerated from scratch afterwards).

## What agents write

`INSTRUCTIONS.md`'s Equations section tells agents to:

- write inline math as `$...$` and display math as a `$$` block on its own lines, with a
  blank line before and after;
- never use code spans or code blocks for math — those are for code, identifiers,
  commands, and file names;
- not put a space just inside the dollars (`$x$`, not `$ x $`), and write a literal
  dollar sign as `\$`;
- keep typing every equation, including ones that exist only as a slide image, and keep
  defining variables; still never link a slide just to show an equation.

Standard viewers (VS Code preview, GitHub, Obsidian) render this directly.

The template's placeholders change from `$name` (`string.Template`) to `{{name}}`, since
the template itself now contains dollar signs.

## Parsing

The shared parser (`mdparse`) adds `mdit-py-plugins`' dollar-math plugin with:
`allow_labels=False`, `allow_space=False` (so `$ x $` is not math), `allow_digits=False`
(so `$5 and $6` is not math), `double_inline=True` (so `$$x$$` inside a sentence is
tolerated as display math). Math in inline code is not math. An unclosed `$$` does not
swallow the rest of the document.

Token types: `math_inline`, `math_inline_double`, `math_block`.

`mdparse.inline_text(children)` returns the plain text of inline tokens with math kept as
its LaTeX source, so titles and captions containing math do not lose it
(markdown-it's `renderInlineAsText` silently drops math tokens).

`finish` does not validate LaTeX; figure-link validation ignores math content.

## HTML export

- Math renders client-side with **KaTeX 0.18.7**, vendored at
  `src/lecnotes/vendor/katex/` (`katex.min.js`, `katex.min.css`, the 20 `fonts/*.woff2`,
  `LICENSE`, and a `VERSION` file). At export time the CSS's `@font-face` sources are
  rewritten to WOFF2 data URIs only (WOFF/TTF fallbacks dropped).
- Inline math is emitted as `<span class="lecnotes-math">LaTeX, HTML-escaped</span>`;
  display math (`math_block`, `math_inline_double`) as
  `<div class="lecnotes-math lecnotes-math-display">…</div>`.
- When — and only when — the document contains math, the page includes the KaTeX CSS
  and JS inline plus a short script that renders every `.lecnotes-math` element with
  `displayMode` from the class, `throwOnError: false` (a bad formula shows its source in
  red) and `trust: false`. Without JavaScript the raw LaTeX remains visible.
- Documents without math are unchanged: no `<script>` at all.
- The "no JavaScript" rule becomes: no JavaScript except the bundled KaTeX renderer, and
  only when the document has math. Still no network requests: no external `src`,
  `href`, `url(`, or `@import`.
- `<title>` and figure captions use `inline_text`, so math in them appears as LaTeX
  source.

Size: about 0.7 MB added to documents with math.

## Notion export

Math passes through unchanged (`$...$`, `$$` blocks). `unwrap` already leaves
`math_block` lines alone. The page title uses `inline_text`. How Notion's Markdown
importer treats `$`/`$$` is unverified and goes on the verify-on-first-import list.

## Dependencies

Runtime: pymupdf, markdown-it-py, mdit-py-plugins. KaTeX is vendored files, not a Python
dependency.

## Testing

- Parser: inline, double-inline and block math become math tokens; `$5 and $6`,
  `$ x $`, and `` `$x$` `` do not; unclosed `$$` stays text; figure links next to math
  still resolve; `inline_text` keeps math source.
- Instructions: rendered text contains `$...$` guidance and a `$$` example, no leftover
  `{{`, and no "plain text" equation wording.
- KaTeX assets: every `@font-face` source is a WOFF2 data URI, no `url(fonts/` remains,
  the JS contains no `</script`.
- HTML: math emitted as escaped LaTeX in the right element; KaTeX included only when
  math exists; math-free output has no `<script>`; math output makes no external loads;
  title/caption keep math source.
- Notion: inline and block math byte-identical in the zip; title keeps math source.
- Real run: regenerated CS 8803 lectures 2 and 3 export with rendered math.
