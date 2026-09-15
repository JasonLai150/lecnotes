# lecnotes — design

**Date:** 2026-08-27
**Status:** approved, pre-implementation

## What this is

A CLI that turns a single lecture deck (`.pdf`, `.pptx`, `.ppt`) into a
self-contained working directory that any coding agent can read in order to write
a teaching document, plus a second command that validates and assembles the
result.

The tool does the deterministic work — rendering, text extraction, figure
detection, figure cropping, validation, assembly. A coding agent does the
writing. The seam between them is a directory on disk, not an API call, so no
part of the tool knows or cares which agent is driving it.

## Background

This generalizes a one-off pipeline built for CS4440 (Database Systems), which
turned 23 lecture decks into 108k words of topic notes. That pipeline's
deterministic half worked well and is carried over; its course-specific half
(hand-written topic maps, a hand-written brief, emphasis outlines distilled from
review decks) is not.

Two findings from that project drive the design:

1. **Slides must be rendered to images, not parsed as text.** Of 1,240 slides,
   1,226 carried a clean text layer — but 758 carried figures that exist only as
   images. Feeding an agent both the PNG and the exact text of each slide means
   diagrams get interpreted by vision while wording stays lossless. Any approach
   that parses presentation XML instead of rendering loses the diagrams, which
   are most of the value.
2. **Figures must be cropped, not embedded as whole slides.** Re-rendering each
   referenced slide cropped to its content box produces a usable figure; a
   full-page screenshot does not.

## Scope

**In scope:** one deck in, one Markdown document out, driven by any agent.

**Out of scope for now**, deliberately:

- Multi-deck / whole-course runs, topic segmentation across decks.
- Calling an LLM API directly. The agent is the driver; the tool is a CLI.
- Export formats beyond Markdown. A seam is left for them; none are built.
- The editorial content of the instructions template (audience, depth, voice).
  Mechanics are specified here; the editorial half ships as a generic default and
  is tuned separately.

## Interface

```
lecnotes prep   <deck.pdf|deck.pptx|deck.ppt> [-o WORKDIR] [--force] [--json]
lecnotes finish <WORKDIR> [--json]
```

Reserved for later, without disturbing either command:
`lecnotes export <WORKDIR> --to notion|html`.

### Workdir layout

`prep lec1.pdf` creates `lec1.notes/` (override with `-o`):

```
lec1.notes/
  INSTRUCTIONS.md     the contract: what to read, what to write, how to link figures
  manifest.json       deck metadata and per-slide rows
  source.pdf          the deck; converted from .pptx if needed
  pages/
    slide-001.png     rendered page, 1400px long edge
    slide-001.txt     exact extracted text for that page
    ...
  NOTES.md            stub; the agent overwrites this
  out/                created by finish
    lec1.md
    figures/
      slide-008.png   cropped to content box
```

The workdir is self-contained and portable. `source.pdf` is copied in because
`finish` re-renders cropped figures from the PDF rather than cropping the page
PNG — a crop re-rendered at 1400px on its own long edge is sharper than a crop
taken out of a 1400px full-page render, which matters for small diagram labels.

### manifest.json

```json
{
  "deck": "lec1",
  "source": "lec1.pdf",
  "source_format": "pdf",
  "converted": false,
  "slides": 47,
  "figures": 29,
  "rendered_long_edge": 1400,
  "pages": [
    {"n": 1, "png": "pages/slide-001.png", "txt": "pages/slide-001.txt",
     "chars": 31, "figure": false}
  ]
}
```

### JSON output

```console
$ lecnotes prep lec1.pdf --json
{"ok":true,"workdir":"lec1.notes","deck":"lec1","slides":47,"figures":29,
 "notes_preserved":false,
 "instructions":"lec1.notes/INSTRUCTIONS.md","write_to":"lec1.notes/NOTES.md",
 "next":"lecnotes finish lec1.notes"}

$ lecnotes finish lec1.notes --json
{"ok":true,"output":"lec1.notes/out/lec1.md","figures_resolved":12}

$ lecnotes finish lec1.notes --json      # agent referenced a slide that isn't there
{"ok":false,"error":"figure_out_of_range","bad_refs":[{"slide":91,"max":47}]}
```

Exit codes: `0` success, `1` usage or validation failure, `2` missing external
dependency.

## Behavior

### prep

0. Derive the **deck name** by slugifying the input stem: lowercase, every run of
   non-alphanumeric characters becomes a single `-`, leading and trailing `-`
   stripped. `lec8-txn,cc.pdf` becomes `lec8-txn-cc`. The deck name sets the
   default workdir (`<deck>.notes/`) and the output filename (`out/<deck>.md`).
1. Detect input format by extension.
   - `.pdf` — used directly.
   - `.pptx` / `.ppt` — converted with `soffice --convert-to pdf`. If `soffice`
     is not on PATH, exit 2 (`missing_converter`) with the
     `brew install --cask libreoffice` hint and the manual-export alternative.
     If conversion runs but produces no PDF, exit 2 (`conversion_failed`).
   - `.key` — exit 1 (`unsupported_format`) pointing at Keynote's PDF export.
     LibreOffice does not open Keynote files reliably, so attempting it would
     fail in a more confusing way.
   - anything else — exit 1 (`unsupported_format`).
2. Render every page to `pages/slide-NNN.png` at 1400px on the long edge, and
   write its extracted text to `pages/slide-NNN.txt`.
3. Flag each page as carrying a figure: it has an embedded image whose
   width × height exceeds 40,000 pixels, or it has more than 12 vector drawings.
   This is a hint telling the agent where to look hard, not a filter — nothing is
   withheld based on it.
4. Write `manifest.json`, `INSTRUCTIONS.md`, and a stub `NOTES.md`.

**1400px** is chosen to sit under the 1568px cap above which vision models
downscale, keeping small diagram labels legible without inflating token cost.

**Existing workdir.** `prep` exits 1 (`workdir_exists`) if the target directory is
already there. With `--force` it re-renders
`pages/`, `manifest.json`, `INSTRUCTIONS.md`, and `source.pdf` — but an existing
`NOTES.md` is **never** overwritten, with or without the flag. Re-prepping a deck
whose notes are already written is a normal thing to want; losing that writing to
a flag is not. The output reports that `NOTES.md` was preserved.

### finish

1. Validate the argument is a workdir (has `manifest.json`); else exit 1
   (`not_a_workdir`).
2. If `NOTES.md` is byte-identical to the stub, exit 1 (`notes_empty`). Building
   an empty document is a mistake, not a success.
3. Scan `NOTES.md` for figure references matching
   `!\[([^\]]*)\]\(figures/slide-(\d{3})\.png\)` — exactly the form
   `INSTRUCTIONS.md` tells the agent to write. Because a workdir holds one deck,
   there is no deck path segment; the CS4440 pipeline needed one and this does
   not.
4. If any reference names a slide outside `1..slides`, exit 1
   (`figure_out_of_range`) listing every offender. This caught real errors in the
   CS4440 project and is the main reason `finish` exists as a separate step.
5. Re-render each referenced slide cropped to its content box into
   `out/figures/`.
6. Copy `NOTES.md` to `out/<deck>.md`.

**Content box.** The union of every text block, image, and vector drawing on the
page, padded by 10pt and clipped to the page. Any single element covering ≥95% of
the page area is treated as backdrop and excluded — Keynote and PowerPoint exports
paint a full-page white rectangle behind every slide, and counting it would make
the content box the entire page and defeat the crop entirely. If the resulting box
is empty, the full page is used.

## Architecture

```
src/lecnotes/
  cli.py            argparse dispatch, --json formatting, exit codes
  workdir.py        owns the layout; create/validate, manifest read/write
  ingest.py         format detection, soffice conversion
  render.py         PDF -> pages/ + manifest rows
  figures.py        content_box, cropped re-render, reference scanning
  instructions.py   fills templates/instructions.md
  templates/
    instructions.md
```

Two boundaries carry the weight:

**`cli.py` does argument parsing, output shaping, and exit codes — nothing else.**
Every other module is a plain function callable and testable without a command
line.

**`workdir.py` is the only module that knows the folder layout.** Both commands
depend on it, so path literals don't scatter across five files.

### Error handling

Every failure raises `LecnotesError(code, message, **detail)`. `cli.py` catches it
in one place and renders it as human text or JSON. That single path is what keeps
the two output modes from drifting — a newly added error is automatically correct
in both.

Codes and their exit status:

| code | exit | raised by |
|---|---|---|
| `unsupported_format` | 1 | prep, on `.key` or an unknown extension |
| `missing_converter` | 2 | prep, when `.pptx`/`.ppt` input finds no `soffice` |
| `conversion_failed` | 2 | prep, when `soffice` runs but emits no PDF |
| `workdir_exists` | 1 | prep, without `--force` |
| `not_a_workdir` | 1 | finish, on a path with no `manifest.json` |
| `notes_empty` | 1 | finish, on an unmodified stub `NOTES.md` |
| `figure_out_of_range` | 1 | finish, on a reference past the last slide |

## Testing

TDD. Fixtures are **synthesized at test time** with pymupdf rather than checked in,
so the repo carries no opaque binary assets and each test states the exact page it
needs.

Cases that must be covered:

- A text-only page flags `figure: false`; a page with a large drawing flags
  `figure: true`.
- **A page with a full-page white rectangle behind a small diagram crops to the
  diagram, not the page.** This is the subtlest logic in the tool and the thing
  most likely to silently regress.
- A page with no content at all falls back to the full page rather than producing
  an empty crop.
- `.pptx` input with `shutil.which` monkeypatched to `None` exits 2 with the
  install hint.
- `NOTES.md` referencing slide 91 of a 47-slide deck exits 1 and names slide 91.
- `prep` over an existing workdir exits 1 with `workdir_exists`; `prep --force`
  over that same workdir with a written `NOTES.md` succeeds and preserves that
  file byte-for-byte.
- Deck-name slugging: `lec8-txn,cc.pdf` yields deck `lec8-txn-cc` and output
  `out/lec8-txn-cc.md`.
- `finish` on a stub `NOTES.md` exits 1 with `notes_empty`.
- Every error code renders in both human and `--json` mode.

## Dependencies

- Python >= 3.11 (the system interpreter here is 3.11.5)
- `pymupdf` — the only runtime dependency
- `pytest` — dev only
- `soffice` (LibreOffice) — optional, needed only for `.pptx`/`.ppt` input

Managed with `uv`:

```sh
uv sync
uv run lecnotes prep lec1.pdf
uv run pytest
```

## Deferred

Recorded so they aren't rediscovered as surprises:

- **Export formats.** The CS4440 project had ~250 lines of working Notion-dialect
  conversion (pipe tables to XML, `$x$` to Notion's inline-math form, unwrapping
  hard-wrapped lines so inline spans survive Notion's paragraph merge). Not ported.
  `export` is reserved as a third verb.
- **Multi-deck runs and topic segmentation.** The CS4440 pipeline mapped 23 decks
  onto 18 topics by hand. Generalizing that is a separate design.
- **Emphasis outlines.** That project distilled review decks into "what the
  instructor stressed" and fed them to writers. Valuable, but inherently
  multi-deck.
- **The editorial half of `INSTRUCTIONS.md`.** Ships as a generic default; tuning
  it is editing one template file, not touching code.

## Amendments (2026-09-14, from the final whole-branch review)

These supersede the sections above wherever they conflict.

**Install.** For real use the tool is installed as a command on PATH:
`uv tool install git+https://github.com/JasonLai150/lecnotes` (or `uv tool install .`
from a checkout). `uv sync` / `uv run` remain the development workflow. `python -m
lecnotes` also works.

**The finish command an agent is told to run.** `INSTRUCTIONS.md` tells the agent to run
`lecnotes finish .` from inside the workdir, which is independent of where the workdir
lives and survives moving it. The `next` field in `prep`'s output is
`lecnotes finish <workdir path>` with the path shell-quoted.

**Deck name.** Casefold the input stem, replace every run of characters that are not
Unicode letters or digits (underscore counts as a separator) with a single `-`, strip
leading/trailing `-`. If the result is empty, the deck name is `deck`.
`lec8-txn,cc.pdf` → `lec8-txn-cc`; `Übung 3.pdf` → `übung-3`; `!!!.pdf` → `deck`.

**Workdir identity.** A directory is a lecnotes workdir only if `manifest.json` parses
as a JSON object containing the keys `deck`, `slides`, `pages`, and
`rendered_long_edge`. Anything else — no manifest, unparseable JSON, a foreign
`manifest.json` — is not a workdir: `finish` raises `not_a_workdir`, and `prep --force`
refuses with `workdir_exists`.

**prep validates before touching disk.** The input file's existence and openability
are checked before the workdir is created or modified. A failed `prep` on a new target
leaves nothing behind. `prep --force` whose source is the workdir's own `source.pdf`
does not fail on copying a file onto itself.

**Figure references.** Slide numbers are zero-padded to at least three digits
(`slide-008.png`, `slide-1000.png`). `finish` also rejects *malformed* figure links:
any Markdown image whose target contains `slide-<digits>.png` but is not exactly
`figures/slide-NNN.png` (for example `pages/slide-002.png`, `./figures/slide-003.png`,
`figures/slide-5.png`, or a link with a title). Malformed and out-of-range references
are both checked before anything is written.

**Error output.** Every JSON error includes the human `message`:
`{"ok": false, "error": "<code>", "message": "<text>", ...detail}`. In `--json` mode an
unexpected exception is reported as `internal_error` rather than a traceback with empty
stdout. `conversion_failed` detail includes the tail of `soffice`'s stderr.

Error codes, full table:

| code | exit | raised by |
|---|---|---|
| `source_not_found` | 1 | prep, when the input path does not exist |
| `unsupported_format` | 1 | prep, on `.key` or an unknown extension |
| `invalid_pdf` | 1 | prep, when the PDF (given or converted) cannot be opened or has no pages |
| `missing_converter` | 2 | prep, when `.pptx`/`.ppt` input finds no `soffice` |
| `conversion_failed` | 2 | prep, when `soffice` runs but emits no PDF |
| `workdir_exists` | 1 | prep, without `--force`, or with `--force` on a non-workdir |
| `not_a_workdir` | 1 | finish, on a path that is not a workdir (see Workdir identity) |
| `notes_empty` | 1 | finish, when `NOTES.md` is missing, empty, or still the stub |
| `figure_out_of_range` | 1 | finish, on a reference past the last slide |
| `figure_malformed` | 1 | finish, on a slide image link not in the exact form |
| `internal_error` | 1 | cli, `--json` mode only, on any unexpected exception |

`notes_empty` compares whitespace-stripped content with the stub, which also catches a
missing or blank file — deliberately stricter than byte-identical.

## Amendments (2026-09-15, from real use)

**Figure links are found by parsing, not pattern matching.** `finish` parses
`NOTES.md` with markdown-it-py (CommonMark, raw HTML disabled, tables and
strikethrough enabled). A caption containing brackets, such as `E_{x~p}[f(x)]`, is a
valid figure reference; a regex had been silently skipping such figures while
reporting success. Links inside inline code or code blocks are ignored. A link title
(`![c](figures/slide-001.png "t")`) is valid. `figure_malformed` now also covers a
slide image link missing its `!`, markup that fails to parse as an image, and a bare
`slide-NNN.png` filename in prose — anything that looks like a figure reference but
would not render as one.

**Dependencies.** Runtime dependencies are pymupdf and markdown-it-py.

**No figure flag.** The per-slide `figure` flag, the manifest's `figures` count, and
the `figures` field of `prep`'s output are removed. The heuristic fired on nearly
every slide of real decks and changed no behavior; its only effect was to suggest
agents could skip images. Manifest page rows are `{"n", "png", "txt", "chars"}`.
Existing workdirs whose manifests still carry the old fields keep working.

**INSTRUCTIONS.md.** The agent is told to view every slide image (the `.txt` layer
can omit equations, labels, or whole slides); to type equations as text rather than
link them as figures; that it may go beyond the slides if each addition is marked
`> **Beyond the slides:**`; that algorithm pseudocode is allowed when faithful to the
slides; and that the deck is `source.pdf` in the workdir.
