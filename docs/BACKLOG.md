# Backlog

Things deliberately left for later, with why and where. Sources: the design specs'
out-of-scope sections, the two final reviews, and the build ledgers under
`docs/superpowers/sdd/`.

Current as of 2026-09-15, after the export fix wave.

## Features

**Push to Notion through its API.** `export --to notion` builds an import zip today.
A `--push` flag would create the page directly and upload figures. Needs a Notion
integration token, a parent page ID, and file uploads. The zip exporter's image
collection (`markdown_doc.local_images`) is the piece to reuse. Deferred because the
zip works offline with no setup.

**Multi-deck runs.** Everything is one deck in, one document out. The CS4440
pipeline mapped many decks onto topics by hand; generalizing that (topic
segmentation across decks, a course overview) is its own design.

**Emphasis outlines.** CS4440 distilled review decks into "what the instructor
stressed" and fed that to writers. Valuable, but inherently multi-deck.

**Math rendering: done (LaTeX + KaTeX in HTML, passthrough to Notion).**

**Observability: token usage and run stats.** No visibility into what a notes run
cost or produced: tokens spent by the writing agent, time taken, words written,
slides covered vs skipped, figures linked. `lecnotes` never calls a model, so token
counts have to come from the agent side (reported into the workdir, or read from the
agent's logs); document-side stats (words, figures, slide coverage, equations) can be
computed by `finish` itself.

**HTML extras.** A table of contents, heading anchors, themes. Useful for
4,000-word notes; not built.

**Smaller HTML.** Figures embed as PNG, so a 20-figure lecture is about 8.5 MB. An
opt-in JPEG re-encode would get it to 1-2 MB at the cost of slight fuzz on text and
lines.

## Output quality (open editorial decisions)

These live in `src/lecnotes/templates/instructions.md`. Settled so far: view every
slide image, type equations, "Beyond the slides" callouts allowed, faithful
pseudocode allowed. Still open, from the writing agents' own feedback:

- **Length and figure targets.** "Compressed" and "prefer showing a diagram" pull in
  opposite directions; agents guessed around 4,000 words and 10-20 figures.
- **What to skip.** "Worked examples that walk through a procedure by hand" is
  ambiguous for derivations and paper case-study slides; recurring "where are we"
  progress slides aren't mentioned.
- **Self-check answers.** Unclear whether questions should come with answers.

## Known issues

- **Re-prepping from the workdir's own `source.pdf` renames the deck to `source`.**
  `prep lec1.notes/source.pdf -o lec1.notes --force` succeeds, but the output becomes
  `out/source.md`. Fix: under `--force`, keep the existing manifest's deck name.
  (`commands.prep`)
- **`.pptx` input converts before checking the workdir exists.** Without `--force`,
  an existing workdir still pays for a LibreOffice conversion before
  `workdir_exists`. Nothing is written. (`commands.prep`)
- **`prep --force` is not atomic.** `pages/` is removed before rendering, so a
  render crash partway through leaves a workdir with no pages. Re-running
  `--force` recovers. (`commands.prep`)
- **Wrapped "Beyond the slides" callouts in Notion.** `unwrap` skips blockquotes, so
  a hard-wrapped `> **bold\n> across**` callout shows literal asterisks after
  import. Current agent-written notes aren't hard-wrapped. (`export_notion.unwrap`)
- **Unreadable files give `internal_error`.** A non-UTF-8 source `.md` or an
  unreadable image surfaces as `internal_error` (or a traceback in human mode)
  instead of a specific code. (`commands.export`)
- **One bad figure link can be listed twice.** `[see slide-021.png](figures/slide-021.png)`
  reports both the href and the text fragment. Cosmetic. (`figures.find_malformed`)
- **A whitespace-only `#` heading** falls back to the file stem for the Notion title
  but stays in the body as an empty heading. (`export_notion.split_title`)
- **Export's `images` count is by target file.** Two links that resolve to one file
  (e.g. symlinks sharing a target) count once, so the number can be lower than the
  zip's image entries. Metadata only. (`commands.export`)
- **Notion title sanitizing can leave a double space** when a control character sits
  between two spaces (`"a \x01 b"` → `"a  b"`). Harmless in a file name.
  (`export_notion.sanitize_filename`)
- **Symlinked `pages/` or `out/figures/`** makes `rmtree` raise a raw `OSError`.
  Nothing is deleted. (`commands.prep`, `commands.finish`)
- **Math in figure captions shows as LaTeX source rather than rendered.**
  Figcaptions use `inline_text`, which keeps `$...$` as plain text; there is no
  KaTeX render target inside a `<figcaption>`. (`export_html.render_html`)
- **A blockquote nested in a list item at 4+ spaces of indentation still leaks
  `>` into display math.** `_strip_blockquote_markers` only undoes the ">"
  markers dollarmath's block rule captures for a top-level blockquote; one
  nested inside a list item's own indentation is not covered.
  (`mdparse._strip_blockquote_markers`)

## Not yet verified in real use

- **PowerPoint input.** LibreOffice isn't installed on the development machine, so
  `.pptx`/`.ppt` conversion has only been exercised with mocked `soffice` calls. The
  tests don't assert the command line it builds.
- **Notion import.** The zip's page title is assumed to come from the `.md` file name
  and images from relative paths; neither has been checked against a real Notion
  import yet, and how the importer treats `$...$` inline math and `$$` blocks.

## Test gaps

Behavior below was verified by hand during review but has no regression test:

- `finish` with `NOTES.md` deleted after `prep` (maps to `notes_empty`).
- A figure link inside a pipe table, at the `finish` level (covered in
  `test_mdparse`).
- An image-only paragraph inside a loose list item or blockquote becoming a
  `<figure>` in HTML.
- `unwrap` on a setext heading, a paragraph directly followed by a list, and a final
  paragraph with no trailing newline.
- `test_image_types` asserts 3 of the 6 MIME entries.

## Code cleanup

- **Layout literals outside `workdir.py`.** The default workdir name
  (`<deck>.notes`), figure file names (`slide-NNN.png`), and output name
  (`<deck>.md`) are built in `commands.py`; `figures.py` hardcodes `figures/`. Move
  them behind `workdir` helpers.
- **Version is defined twice**, in `pyproject.toml` and `src/lecnotes/__init__.py`.
  Read it with `importlib.metadata.version("lecnotes")` instead.
- **`deck_47` fixture** is used only by its own self-test.
- **Unused `import json`** in `tests/test_prep.py`.
- **`mdparse.py`** lost the note explaining why one parser instance is safe to reuse
  across calls.
- **`export_notion.py`** resolves `base_dir` twice.
