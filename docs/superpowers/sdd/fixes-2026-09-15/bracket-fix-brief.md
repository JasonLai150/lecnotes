# Fix: figure links silently dropped by `finish`

Repo: /Users/jasonlai150/Documents/GitHub/lecnotes (Python, uv; run tests with `uv run pytest`; 177 passing now).

## Bug (reported from real use)
A caption containing `]` — e.g. `![E_{x~p}[f(x)] estimator](figures/slide-019.png)` — makes `finish` skip that figure with no error and `ok: true`. Cause: `src/lecnotes/figures.py` `REF_RE` and `IMAGE_RE` match the caption with `[^\]]*`, so neither pattern matches and `find_malformed` never sees the link. Same root, same silent drop:
- an unbalanced `[` in a caption (`![maps [0,1) to R](figures/slide-020.png)`) — not an image to any Markdown parser, raw markup left as text
- a missing `!` (`[see](figures/slide-021.png)`) — a plain link, the figure never shows
Also wrong today: example links inside inline code or fenced code blocks are counted as figure references.

## Fix
Replace regex scanning of image links with parsing by `markdown-it-py`, plus a safety net for links that fail to parse.

1. Add runtime dependency `markdown-it-py>=3` in pyproject.toml (`uv add markdown-it-py`), committing the uv.lock change. The spec's dependency rule is being amended to "pymupdf and markdown-it-py".
2. In `src/lecnotes/figures.py`, parse with `MarkdownIt("commonmark", {"html": False})` and walk inline children tokens:
   - `find_refs(markdown) -> list[int]` (same contract: sorted, de-duplicated): `image` tokens whose `src` attr fully matches `figures/slide-(\d{3}|[1-9]\d{3,})\.png`.
   - `find_malformed(markdown) -> list[str]` (same contract: document order, de-duplicated), collecting:
     a. `image` tokens whose `src` contains `slide-\d+\.png` but does not fully match the strict form → the `src`
     b. `link_open` tokens whose `href` contains `slide-\d+\.png` (missing `!`) → the `href`
     c. `text` tokens containing `slide-\d+\.png` (link markup that failed to parse, or a bare filename in prose) → each `\S*slide-\d+\.png\S*` match
     Tokens of type `code_inline`, `fence`, `code_block` are never inspected (they are not text/image/link tokens, so walking only image/link_open/text achieves this — verify with tests).
   - A link title (`![t](figures/slide-001.png "t")`) is now VALID: markdown-it separates the title, the image resolves, and finish's crop exists. Update the existing test that asserts it is malformed.
   - Remove `IMAGE_RE`/`SLIDE_PNG_RE`/`REF_RE` if no longer used; keep a module-level compiled strict-src pattern. Keep one shared `MarkdownIt` instance and a small helper that yields the relevant tokens, so the export feature can reuse it later.
3. `figure_malformed` error message in `commands.finish`: name the offending links and say the usual causes — unbalanced `[` or `]` in the caption, a missing `!`, or a path other than `figures/slide-NNN.png`.
4. `src/lecnotes/templates/instructions.md`: the "Including a figure" note currently says links take "no link title" — remove that clause (titles are fine now). Do NOT make any other template edits; editorial changes are coming separately.

## Tests (write first; see each fail before fixing)
In tests/test_figures_refs.py (find_refs) and the find_malformed tests:
- `![E_{x~p}[f(x)] estimator](figures/slide-019.png)` → find_refs [19], malformed []
- `![maps [0,1) to R](figures/slide-020.png)` → find_refs [], malformed contains an entry with `slide-020.png`
- `[see](figures/slide-021.png)` → malformed ["figures/slide-021.png"]
- `` `![x](figures/slide-022.png)` `` and a fenced block containing `![x](figures/slide-023.png)` → find_refs [], malformed []
- `![t](figures/slide-001.png "title")` → find_refs [1], malformed []
- every existing case still holds (pages/slide-002.png, ./figures/slide-003.png, figures/slide-5.png, figures/slide-0001.png malformed; slide-1000 valid; assets/logo.png ignored; sort/dedupe)
In tests/test_finish.py: a NOTES.md whose only figure has `[f(x)]` in its caption → finish resolves it (figures_resolved 1, file exists); a NOTES.md with an unbalanced `[` caption → `figure_malformed`, nothing written.

## Constraints
- Commit on main, do NOT push, do not commit anything under docs/superpowers/sdd/.
- Commit messages end with `Co-Authored-By: Claude <your model name> <noreply@anthropic.com>` then `Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy`.
- Full suite must pass with no warnings.
- Don't touch anything else (the has-figure flag, export feature, other template text are out of scope).
