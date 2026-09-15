## Global Constraints

- Runtime dependencies are exactly `pymupdf`, `markdown-it-py`, `mdit-py-plugins`. KaTeX is vendored files, not a dependency.
- Dollar-math plugin options, exactly: `allow_labels=False, allow_space=False, allow_digits=False, double_inline=True`.
- Math token types: `math_inline`, `math_inline_double`, `math_block`.
- KaTeX version `0.18.7`, vendored at `src/lecnotes/vendor/katex/`: `katex.min.js`, `katex.min.css`, `fonts/*.woff2` (20 files), `LICENSE`, `VERSION`.
- HTML math markup: inline `<span class="lecnotes-math">…</span>`; display `<div class="lecnotes-math lecnotes-math-display">…</div>`; content is the HTML-escaped LaTeX.
- KaTeX render options: `displayMode` from the class, `throwOnError: false`, `trust: false`.
- HTML without math contains no `<script>`. HTML with math makes no external loads (no `src="http`, `href="http`, `url(http`, `url(fonts/`, `@import`, `<link`).
- Leaf modules (`mdparse`, `markdown_doc`, `export_html`, `export_notion`, `figures`, `katex`) never raise `LecnotesError`.
- Commit on `main` after every task; do not push; do not commit `docs/superpowers/sdd/`. Commit messages: subject, blank line, `Co-Authored-By: Claude <model name> <noreply@anthropic.com>`, `Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy`, each on its own line.
- Full suite passes with no warnings after every task.

## File Structure

| File | Change |
|---|---|
| `pyproject.toml`, `uv.lock` | add `mdit-py-plugins` |
| `src/lecnotes/mdparse.py` | dollar-math in `new_parser`; new `inline_text` |
| `src/lecnotes/instructions.py` | `{{name}}` placeholders instead of `string.Template` |
| `src/lecnotes/templates/instructions.md` | new Equations section; `{{deck}}`, `{{slides}}`, `{{source_name}}` |
| `src/lecnotes/vendor/__init__.py`, `src/lecnotes/vendor/katex/__init__.py` | new (empty; regular packages for importlib.resources) |
| `src/lecnotes/vendor/katex/*` | vendored KaTeX 0.18.7 |
| `src/lecnotes/katex.py` | new: `KATEX_VERSION`, `katex_css()`, `katex_js()` |
| `src/lecnotes/export_html.py` | math render rules, conditional KaTeX, `inline_text` for title/caption |
| `src/lecnotes/export_notion.py` | `inline_text` for the title |
| `README.md` | math note |
| tests | `test_mdparse.py`, `test_instructions.py`, `test_katex.py` (new), `test_export_html.py`, `test_export_notion.py` |

---

