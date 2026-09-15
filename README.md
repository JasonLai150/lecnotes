# lecnotes

Turn one lecture deck into a working directory a coding agent can read, then
assemble what it writes into a document with cropped figures.

The tool does the deterministic half — rendering, text extraction, figure
detection and cropping, validation, assembly. An agent does the writing. The seam
between them is a directory on disk, so nothing here depends on which agent you
use.

## Install

```sh
uv sync
```

`.pptx` and `.ppt` input additionally needs LibreOffice
(`brew install --cask libreoffice`). PDF input needs nothing extra.

## Use

```sh
uv run lecnotes prep lec13.pdf
```

That creates `lec13.notes/`:

```
lec13.notes/
  INSTRUCTIONS.md    what to read, what to write, how to link figures
  manifest.json      per-slide metadata, including which slides carry figures
  source.pdf         the deck
  pages/
    slide-001.png    the rendered slide — diagrams exist only here
    slide-001.txt    that slide's exact text
  NOTES.md           stub; the agent replaces this
```

Point any coding agent at `lec13.notes/INSTRUCTIONS.md`. It reads `pages/`, writes
`NOTES.md`, and runs:

```sh
uv run lecnotes finish lec13.notes
```

which validates every figure link, re-renders each referenced slide cropped to its
content, and writes `lec13.notes/out/lec13.md` alongside `out/figures/`.

## For agents

Both commands take `--json`:

```console
$ lecnotes prep lec13.pdf --json
{"ok":true,"workdir":"lec13.notes","deck":"lec13","slides":47,"figures":29,
 "notes_preserved":false,"instructions":"lec13.notes/INSTRUCTIONS.md",
 "write_to":"lec13.notes/NOTES.md","next":"lecnotes finish lec13.notes"}
```

Exit codes: `0` success, `1` usage or validation failure, `2` missing external
dependency. Failures print `{"ok": false, "error": "<code>", ...}`.

Figure links must be written exactly as `![caption](figures/slide-NNN.png)`, with
the slide number zero-padded to three digits. Linking a slide the deck does not
have fails the build and names the offender.

`prep` never overwrites a `NOTES.md` that already exists, with or without
`--force`.

## Why slides get rendered rather than parsed

In the course this came from, 1,226 of 1,240 slides carried a clean text layer —
but 758 carried figures that exist only as images. Giving an agent both the PNG
and the exact text of each slide means diagrams get read by vision while the
wording stays lossless. Parsing presentation XML instead would lose the diagrams,
which are most of the value.

## Development

```sh
uv run pytest
```

Test fixtures are PDFs synthesized at test time rather than checked in, so every
test states its own input.
