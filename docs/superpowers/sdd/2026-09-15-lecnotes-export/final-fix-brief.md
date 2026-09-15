# Export final-review fix wave — brief

Repo: /Users/jasonlai150/Documents/GitHub/lecnotes. `lecnotes export` is complete (259 tests). A whole-feature review found the issues below. The binding decisions are in the section **"Amendments (2026-09-15, from the final whole-feature review)"** at the end of `docs/superpowers/specs/2026-09-15-lecnotes-export-design.md` — read it; it supersedes earlier spec text where they conflict.

Fix everything below, test-first. A few coherent commits. Do not push; don't commit docs/superpowers/sdd/.

## Important

1. **`invalid_output` bypass (commands.py ~232).** `dest.resolve() == source.resolve()` compares path strings; on macOS APFS (case-insensitive) `export n.md --to html -o N.MD` overwrote `n.md`; hard links also bypass it. Replace with: `dest.exists() and os.path.samefile(dest, source)`. Also raise `invalid_output` when `dest.parent.exists() and not dest.parent.is_dir()`. Keep the existing `dest.is_dir()` check. Tests: a case-changed `-o` (skip with `pytest.skip` when the tmp filesystem is case-sensitive — detect by creating `a.txt` and checking `A.TXT` exists), a hard link to the source (`os.link`), a symlink to the source, and a parent-is-a-file `-o`; each → `invalid_output` and the source bytes unchanged / nothing written.
2. **`-o <workdir>/NOTES.md` overwrites NOTES.md (commands.py 201-251).** In workdir mode also raise `invalid_output` when `dest` exists and is the same file as the workdir's NOTES.md. Restructure minimally (e.g. `_export_source` returns `(markdown_path, workdir_root_or_None)`). Test: workdir export with `-o` pointing at NOTES.md (both formats) → `invalid_output`, NOTES.md unchanged.
3. **`not_finished` advice can lose edits (commands.py 180-190).** Reword the "differ" message per the amendment: say NOTES.md and out/<deck>.md differ; run `lecnotes finish` if NOTES.md is the version to keep; if out/<deck>.md was edited on purpose, export it directly: `lecnotes export <that path> --to ...`. Include the out path in the message. Update the test that asserts on the message (still must mention NOTES.md) and assert the out/<deck>.md path is mentioned.

## Also fix

4. **Notion title sanitizing (export_notion.py `sanitize_filename`).** In order: collapse `\s+` → single space; drop control characters (`unicodedata.category(c).startswith("C")`); `\s*:\s*` → ` - `; remaining `/ \ * ? " < > |` → `-`; strip; cap at `TITLE_MAX`; strip again. Update `test_sanitize_filename` (the expected string changes because of the colon rule — recompute it by hand and put the reasoning in a comment) and add cases: `"Learning from Data: Imitation"` → `"Learning from Data - Imitation"`; a setext two-line H1 through `split_title` gives a one-line name; a tab and `\x01` removed/collapsed.
5. **Zip entry names from `src` (export_notion.py ~104, markdown_doc.py).**
   - Add to `LocalImage` a property `relpath -> str`: `posixpath.normpath(unquote(src))` (strip a leading `./` via normpath).
   - `LocalImage.mime` follows the extension of `unquote(src)`, not the resolved path.
   - `images_outside`: an image is outside when `unquote(src)` is absolute (`os.path.isabs` or starts with `/`) or its `relpath` is `..` or starts with `../`. Drop the resolved-path `is_relative_to` logic (keep the function signature).
   - `write_notion_zip`: store each image at `relpath`, reading bytes from `image.path` (resolved); de-duplicate by `relpath`.
   - Tests: symlinked figure (`figures/slide-001.png` → `cache/abc.png`) is stored as `figures/slide-001.png`; absolute src inside base_dir is reported by `images_outside`; `./figures/x.png` and `figures/x.png` produce one entry `figures/x.png`; a symlink named `.png` whose target is `.bin` still has mime `image/png`.
6. **No leftover `.tmp` (export_notion.py 99-105).** Wrap the zip write so any exception unlinks the tmp file and re-raises. Test by monkeypatching `zipfile.ZipFile.write` to raise, asserting no `.tmp` remains.
7. **HTML title = first top-level H1 (export_html.py ~98).** Require `token.level == 0`. Test: `> # Quoted\n\n# Real\n` → `<title>Real</title>`.
8. **`image_not_found` reason.** `missing_images` stays as is for its callers, but the message in `commands.export` must separate missing files from unsupported types, e.g. `missing: a.png, b.png; unsupported type (use png, jpg, jpeg, gif, svg, webp): c.bmp`. Keep detail `missing` = all offenders in order (unchanged contract), and add detail `unsupported` = the unsupported subset. Test the message shape.
9. **finish: case-insensitive slide shape (figures.py `SLIDE_PNG_RE`, `LOOSE_TEXT_RE`).** Compile with `re.IGNORECASE`, so `![](figures/slide-002.PNG)` is `figure_malformed`. Keep `STRICT_SRC_RE` case-sensitive (only lowercase `.png` is a valid reference because finish writes lowercase files). Test in test_figures_refs.py and a finish-level test.
10. **Stale wording.** README: "Both commands take `--json`" → all three; add the export JSON result shape to the "For agents" section next to the prep one; mention `invalid_output`/`not_finished`/`image_not_found`/`image_outside_root` briefly where exit codes are described. `commands.py` module docstring: not "two verbs". Fix the `deck_47` comment in tests/conftest.py ("slide 8 carries a figure") — it no longer means anything; say it has 20 line drawings.

## Out of scope — do NOT do
- Joining wrapped blockquote paragraphs in `unwrap`.
- Mapping non-UTF-8 source files or unreadable images to specific error codes (beyond item 1's parent-is-a-file case).
- `find_malformed` double-listing.

## Constraints
- Runtime deps stay pymupdf + markdown-it-py. Leaf modules (`markdown_doc`, `mdparse`, `export_html`, `export_notion`, `figures`) never raise `LecnotesError`.
- Every error code stays covered in both CLI output modes (the static guard in test_cli.py enforces this).
- Commit messages: subject, blank line, `Co-Authored-By: Claude <your model name> <noreply@anthropic.com>`, `Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy` on their own lines.
- Full suite green, no warnings.
