# lecnotes export — design

**Date:** 2026-09-15
**Status:** approved design, pre-implementation
**Extends:** `docs/superpowers/specs/2026-08-27-lecnotes-design.md` (including its amendments)

## What this is

A third verb that turns Markdown notes into formats people actually read in:

```
lecnotes export <workdir | file.md> --to html|notion [-o OUT] [--json]
```

The Markdown `finish` produces stays the **source of truth**: an intermediary that is
also usable on its own. Exporters derive other formats from it and never modify it.

## Why

`out/<deck>.md` references its figures by relative path (`figures/slide-008.png`).
Anything that takes the Markdown file alone — pasting into Notion, a plain text
viewer, attaching it to a message — loses every image. Readers need either one
self-contained file or a package a target app knows how to import.

## Scope

**In scope:** `--to html` (one self-contained file) and `--to notion` (an
import-ready zip).

**Out of scope for now:**

- Pushing to Notion through its API. The zip exporter is built so a later `--push`
  can reuse the same image collection; nothing is designed for it yet.
- Rendering math. Formulas stay as code spans, exactly as the Markdown has them.
- A table of contents, heading anchors, themes, or any styling configuration.
- Re-encoding figures. PNG is embedded as-is.

## Input resolution

`export` accepts one path:

| Path | Markdown used | Images resolve relative to |
|---|---|---|
| a lecnotes workdir | `out/<deck>.md` | `out/` |
| a file ending in `.md` | that file | the file's directory |
| does not exist | — | `source_not_found` (exit 1) |
| anything else | — | `unsupported_format` (exit 1) |

For a workdir:

- If `out/<deck>.md` does not exist, raise `not_finished` (exit 1): `finish` has not
  been run.
- If `NOTES.md` differs from `out/<deck>.md`, raise `not_finished` (exit 1) with a
  message saying `NOTES.md` changed since the last `finish`. Exporting silently
  stale notes is the failure this prevents.

A workdir is recognized with the existing `workdir.is_workdir`.

## Images

Image links are found by parsing the Markdown with `markdown-it-py` — the same
parser that renders the HTML — so both exporters agree exactly on what counts as an
image.

Each image `src` is classified:

- **Remote** (`http://`, `https://`) or **data URI** (`data:`): left untouched. It is
  never fetched; `export` makes no network requests.
- **Local**: resolved against the Markdown's directory. Every local image must exist
  as a file. All missing ones are collected and reported together as
  `image_not_found` (exit 1, detail `missing: [<src as written>, ...]` in document
  order, de-duplicated) **before any output is written**.

Supported local image types, by extension (case-insensitive): `.png`, `.jpg`,
`.jpeg`, `.gif`, `.svg`, `.webp`. A local image with any other extension counts as
`image_not_found` with the reason in the message.

## Output location

- HTML default: `<markdown dir>/<markdown stem>.html`
- Notion default: `<markdown dir>/<markdown stem>-notion.zip`
- `-o/--out PATH` writes to exactly `PATH` instead.

Outputs are derived and regenerable, so an existing output file is overwritten.
(This is the opposite of `NOTES.md`, which `prep` never overwrites — that is
writing; these are builds.)

## `--to html`

One self-contained HTML file.

- Rendered with `markdown-it-py` using the CommonMark preset with **raw HTML
  disabled** (any HTML in the Markdown is escaped, not rendered) and **tables**
  and **strikethrough** enabled.
- Every local image is embedded as a `data:<mime>;base64,...` URI.
- A paragraph whose only content is a single image becomes
  `<figure><img ...><figcaption>alt text</figcaption></figure>`. If the alt text is
  empty, no `<figcaption>` is emitted. Images inline with other text stay inline.
- `<title>`: the text of the first level-1 heading; if there is none, the Markdown
  file's stem.
- Styling is a single inline `<style>` block: readable measure (about 46rem),
  system font stack, styled tables and code blocks, `img { max-width: 100% }`,
  light and dark palettes via `prefers-color-scheme`, and print rules that avoid
  breaking inside figures, tables, and code blocks.
- No JavaScript. No external stylesheets, fonts, or requests of any kind — the file
  renders identically offline, forever.
- `<meta charset="utf-8">` and a viewport meta tag.

## `--to notion`

A zip for Notion's importer (Settings → Import → Markdown).

- The zip contains one Markdown file plus every local image, each stored at its path
  relative to the Markdown's directory (so `figures/slide-008.png` stays
  `figures/slide-008.png` and the link keeps resolving inside the zip).
- **Page title.** Notion names an imported page after the file. The Markdown file
  inside the zip is named after the first level-1 heading, and that heading line is
  removed from the body so the title does not appear twice. With no level-1
  heading, the file keeps its original stem and the body is unchanged. Filename
  sanitization: characters `/ \ : * ? " < > |` become `-`, surrounding whitespace is
  trimmed, length is capped at 100 characters, and an empty result falls back to the
  original stem.
- **Unwrapping.** Hard-wrapped prose lines are joined so each paragraph, list item,
  and blockquote line is one line. Notion merges wrapped lines into a paragraph but
  does not re-parse inline spans across the break, so `**bold**` straddling a wrap
  shows literal asterisks. Fenced code blocks and pipe tables are left exactly as
  they are. (Ported from the CS4440 `to_notion.unwrap`, which fixed exactly this.)
- A local image whose resolved path is outside the Markdown's directory (for
  example `../shared/x.png`) raises `image_outside_root` (exit 1, detail
  `outside: [<src as written>, ...]`), because a zip entry cannot safely climb out
  of the archive root. This check applies to `--to notion` only; HTML embeds such
  images normally.
- No other dialect conversion (no Notion XML tables, no math rewriting): the
  importer handles standard Markdown.
- To verify on the first real import: that the page title comes from the file name
  and images appear. The design is robust either way — if Notion instead uses the
  first heading, the file name still yields the same title.

## Result

```json
{"ok": true, "format": "html",   "source": ".../out/lec1.md", "output": ".../out/lec1.html",       "images": 20, "bytes": 8912345}
{"ok": true, "format": "notion", "source": ".../out/lec1.md", "output": ".../out/lec1-notion.zip", "images": 20, "bytes": 6512345}
```

`images` counts distinct local images packaged or embedded. `bytes` is the output
file's size.

Human output mirrors `prep`/`finish`: the output path, then an indented line with the
image count and size.

## Errors

New codes, added to the existing table:

| code | exit | raised by |
|---|---|---|
| `not_finished` | 1 | export, on a workdir with no `out/<deck>.md` or a `NOTES.md` that changed since `finish` |
| `image_not_found` | 1 | export, on local images that are missing or of an unsupported type |
| `image_outside_root` | 1 | export `--to notion`, on local images outside the Markdown's directory |

`source_not_found` and `unsupported_format` are reused for input resolution, with
export-specific messages.

## Architecture

| File | Responsibility |
|---|---|
| `src/lecnotes/markdown_doc.py` | `resolve_markdown(path) -> (md_path, base_dir)`; `find_images(markdown) -> list[str]`; `classify` local vs remote; `check_local_images(...)` raising `image_not_found` |
| `src/lecnotes/export_html.py` | `render_html(markdown, base_dir, title_fallback) -> str` |
| `src/lecnotes/export_notion.py` | `unwrap(markdown) -> str`; `build_notion_zip(markdown, base_dir, dest, stem) -> None` |
| `src/lecnotes/commands.py` | `export(target, fmt, out=None) -> dict`: resolve, validate, dispatch, report |
| `src/lecnotes/cli.py` | the `export` subparser and its human reporter — nothing else |

Dependency direction stays one-way: `cli` → `commands` → `markdown_doc`,
`export_html`, `export_notion` → `workdir`, `errors`. The exporters import neither
`commands` nor `cli`.

## Dependencies

The runtime-dependency rule changes from "pymupdf only" to **pymupdf and
markdown-it-py**. `markdown-it-py` is pure Python and is the one addition; Python's
standard library has no Markdown renderer.

## Testing

Test-first, with fixtures synthesized at test time: Markdown strings written to
`tmp_path`, and tiny PNGs made with pymupdf.

- HTML: local images become `data:image/png;base64,` URIs and no local `src`
  remains; an image-only paragraph renders as `<figure>` with `<figcaption>`; empty
  alt gives no figcaption; an inline image stays inline; pipe tables render as
  `<table>`; raw `<script>` in the Markdown is escaped; remote and data-URI images
  are untouched; `<title>` from the first H1 and the stem fallback; the output has
  no `http` references other than remote images the Markdown itself contained.
- Image validation: every missing image is listed, in order, de-duplicated; an
  unsupported extension is reported; nothing is written on failure.
- Notion: zip entry names; the Markdown entry named from the H1 with the H1 removed
  from the body; stem fallback; filename sanitization; unwrapping joins wrapped
  prose but leaves code fences and tables untouched; images stored at relative
  paths; `../` images raise `image_outside_root` and write nothing.
- Input resolution: workdir → `out/<deck>.md`; `.md` file; missing path; non-`.md`
  file; workdir before `finish`; workdir with `NOTES.md` edited after `finish`.
- Output: default paths, `-o`, overwrite of an existing output.
- CLI: `export` in human and `--json` modes; the three new codes added to the
  existing every-code-in-both-modes scenarios (the static guard test fails until
  they are).
- End to end: export the CS 8803 lecture-1 workdir to both formats and open the
  HTML.
