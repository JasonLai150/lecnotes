## Global Constraints

- Runtime dependencies are exactly `pymupdf` and `markdown-it-py`. Add no others.
- The Markdown is the source of truth: exporters never modify the input `.md`, `NOTES.md`, or anything in `pages/`.
- `export` makes **no network requests**; remote (`http://`, `https://`, `//`) and `data:` images are never fetched and are left untouched.
- Supported local image types (case-insensitive): `.png` → `image/png`, `.jpg`/`.jpeg` → `image/jpeg`, `.gif` → `image/gif`, `.svg` → `image/svg+xml`, `.webp` → `image/webp`.
- New error codes, all exit 1: `not_finished`, `image_not_found`, `image_outside_root`. Reused: `source_not_found`, `unsupported_format`.
- All validation happens **before** any output is written. Outputs overwrite existing files.
- HTML output: no JavaScript, no external stylesheets/fonts/requests, raw HTML in Markdown escaped, `<meta charset="utf-8">`.
- Notion zip: Markdown entry named from the first level-1 heading (sanitized: `/ \ : * ? " < > |` → `-`, trimmed, capped at 100 chars, empty → original stem), that heading removed from the body; images at their paths relative to the Markdown's directory.
- `LecnotesError` is raised only from `commands.py` and `ingest.py`/`workdir.py` (existing). New leaf modules raise nothing.
- Exit codes: `0` success, `1` usage or validation failure, `2` missing external dependency.
- Commit after every task on `main`; do not push; do not commit anything under `docs/superpowers/sdd/`. Commit messages end with `Co-Authored-By: Claude <model name> <noreply@anthropic.com>` then `Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy`.
- Full test suite passes with no warnings after every task.

## File Structure

| File | Responsibility |
|---|---|
| `src/lecnotes/mdparse.py` (new) | `new_parser()`, shared `PARSER`, `inline_tokens()` — the one markdown-it configuration |
| `src/lecnotes/figures.py` (modify) | uses `mdparse` instead of its own `_MD` instance |
| `src/lecnotes/markdown_doc.py` (new) | `find_images`, `is_external`, `LocalImage`, `local_images`, `missing_images`, `IMAGE_TYPES` |
| `src/lecnotes/export_html.py` (new) | `render_html(markdown, base_dir, title_fallback) -> str` |
| `src/lecnotes/export_notion.py` (new) | `unwrap`, `sanitize_filename`, `split_title`, `images_outside`, `write_notion_zip` |
| `src/lecnotes/commands.py` (modify) | `export(target, fmt, out=None) -> dict` and its input resolution |
| `src/lecnotes/cli.py` (modify) | `export` subparser, `_report_export` |
| `tests/conftest.py` (modify) | `make_png` helper + `png` fixture |
| `tests/test_mdparse.py`, `tests/test_markdown_doc.py`, `tests/test_export_html.py`, `tests/test_export_notion.py`, `tests/test_export.py` (new) | unit/integration tests |
| `tests/test_cli.py` (modify) | export CLI tests + three new `ERROR_SCENARIOS` |
| `README.md` (modify) | an "Export" section |

Dependency direction: `cli` → `commands` → {`markdown_doc`, `export_html`, `export_notion`, `figures`} → `mdparse`. Nothing imports `commands` or `cli`.

---

