# lecnotes

Turn one lecture deck into a working directory a coding agent can read, then
assemble what it writes into a document with cropped figures.

The tool does the deterministic half — rendering, text extraction, figure
detection and cropping, validation, assembly. An agent does the writing. The seam
between them is a directory on disk, so nothing here depends on which agent you
use.

## Install

Install it as a command on your `PATH`, so the agent can run it too:

```sh
uv tool install git+https://github.com/JasonLai150/lecnotes
```

or, from a checkout, `uv tool install .`. `python -m lecnotes` works as well.

`.pptx` and `.ppt` input additionally needs LibreOffice
(`brew install --cask libreoffice`). PDF input needs nothing extra.

## Use

```sh
lecnotes prep lec13.pdf
```

That creates `lec13.notes/`:

```
lec13.notes/
  INSTRUCTIONS.md    what to read, what to write, how to link figures
  manifest.json      per-slide metadata
  source.pdf         the deck
  pages/
    slide-001.png    the rendered slide — every one gets viewed
    slide-001.txt    that slide's text — can be incomplete; equations and
                      diagrams often exist only in the image
  NOTES.md           stub; the agent replaces this
```

Point any coding agent at `lec13.notes/INSTRUCTIONS.md`. It reads `pages/`, writes
`NOTES.md`, and runs, from inside the workdir:

```sh
lecnotes finish .
```

That validates every figure link, re-renders each referenced slide cropped to its
content, and writes `lec13.notes/out/lec13.md` alongside `out/figures/`. From
anywhere else, pass the workdir path instead; `prep` prints the exact command,
with the path shell-quoted, as its `next` step.

## Export

The Markdown `finish` writes is the source of truth. `export` turns it into
something easier to read or share, without changing it:

```sh
lecnotes export lec13.notes --to html     # lec13.notes/out/lec13.html
lecnotes export lec13.notes --to notion   # lec13.notes/out/lec13-notion.zip
```

- **HTML** is one self-contained file: figures are embedded, styles are inline,
  there is no JavaScript and nothing loads from the network. Open it in any
  browser, or print it to PDF.
- **Notion**: in Notion, go to Settings → Import → Markdown and choose the zip.
  The page is named after the notes' title, and figures come through. (Pasting
  the `.md` alone loses the images; the zip keeps them together.)

Equations are written as LaTeX (`$...$` inline, `$$` blocks), which VS Code,
GitHub and Obsidian preview directly. The HTML export renders them with a copy of
KaTeX embedded in the file (added only when the notes contain math, about 0.7 MB);
the Notion zip passes them through unchanged.

`export` also accepts any `.md` file, resolving images relative to it, and `-o`
sets the output path. On a workdir it refuses to export while `NOTES.md` and
`out/<deck>.md` differ, so you never share a stale copy: run `finish` again, or,
if you edited `out/<deck>.md` on purpose, export that file directly.

## For agents

All three commands take `--json`:

```console
$ lecnotes prep lec13.pdf --json
{"ok":true,"workdir":"lec13.notes","deck":"lec13","slides":47,
 "notes_preserved":false,"instructions":"lec13.notes/INSTRUCTIONS.md",
 "write_to":"lec13.notes/NOTES.md","next":"lecnotes finish lec13.notes"}

$ lecnotes export lec13.notes --to html --json
{"ok":true,"format":"html","source":"lec13.notes/out/lec13.md",
 "output":"lec13.notes/out/lec13.html","images":12,"bytes":2481734}
```

Exit codes: `0` success, `1` usage or validation failure, `2` missing external
dependency. Failures print `{"ok": false, "error": "<code>", "message": "<text>", ...}`.
For `export`, the validation failures are `not_finished` (the workdir has no
`out/` Markdown yet, or `NOTES.md` and it differ), `image_not_found` (an image is
missing or not a supported type), `image_outside_root` (`--to notion` only: an
image link is absolute or climbs out of the Markdown's folder) and
`invalid_output` (`-o` is a directory, sits under a file, or is the Markdown being
exported or the workdir's `NOTES.md`). Nothing is written when any of them occur.

Figure links must be written exactly as `![caption](figures/slide-NNN.png)`, with
the slide number zero-padded to three digits. A slide image link in any other form
(`pages/slide-002.png`, `./figures/...`, `slide-5.png`) fails with
`figure_malformed`; linking a slide the deck does not have fails with
`figure_out_of_range`. Both name every offender.

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
uv sync
uv run pytest
uv run lecnotes prep lec13.pdf   # the checkout's version, without installing it
```

Test fixtures are PDFs synthesized at test time rather than checked in, so every
test states its own input.
