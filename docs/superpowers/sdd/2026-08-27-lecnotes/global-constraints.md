## Global Constraints

- Python `>=3.11`. The system interpreter is 3.11.5.
- `pymupdf` is the **only** runtime dependency. Do not add others.
- Rendered page long edge is **1400** pixels. Below the 1568px vision downscale cap.
- Figure-detection heuristic: an embedded image with `width * height > 40_000`, **or** more than **12** vector drawings.
- Content-box backdrop threshold: any single element covering **>= 95%** of page area is excluded as backdrop.
- Content-box padding: **10** points, then clipped to the page rect.
- Figure reference form, exactly: `![alt](figures/slide-NNN.png)` with `NNN` zero-padded to 3 digits.
- Deck slug rule: lowercase, every run of non-alphanumerics becomes one `-`, strip leading/trailing `-`.
- Exit codes: `0` success, `1` usage or validation failure, `2` missing external dependency.
- Error codes and exits: `unsupported_format` 1, `missing_converter` 2, `conversion_failed` 2, `workdir_exists` 1, `not_a_workdir` 1, `notes_empty` 1, `figure_out_of_range` 1.
- `NOTES.md` is **never** overwritten by `prep`, with or without `--force`.
- Commit after every task. End every commit message with these two lines, verbatim:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy`
- Do not push. The controller pushes after each task's review.

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | uv/pip metadata, dep pins, `lecnotes` console script |
| `src/lecnotes/__init__.py` | `__version__` only |
| `src/lecnotes/errors.py` | `LecnotesError`, the one exception type, with `code`/`message`/`detail`/`exit_code` |
| `src/lecnotes/naming.py` | `slugify()` — deck-name derivation, used by ingest and workdir |
| `src/lecnotes/workdir.py` | layout constants, `create()`, `load_manifest()`, `save_manifest()`, `is_workdir()` |
| `src/lecnotes/figures.py` | `content_box()`, `crop_render()`, `find_refs()` — pure PDF/text functions |
| `src/lecnotes/render.py` | `render_deck()` — PDF to `pages/` plus manifest rows |
| `src/lecnotes/ingest.py` | `resolve_source()` — extension dispatch and `soffice` conversion |
| `src/lecnotes/templates/instructions.md` | the agent-facing contract text |
| `src/lecnotes/instructions.py` | `render_instructions()` — fills that template |
| `src/lecnotes/commands.py` | `prep()` and `finish()` — orchestration, returns result dicts |
| `src/lecnotes/cli.py` | argparse, `--json` shaping, exit codes |
| `tests/conftest.py` | `synth_pdf()` — builds fixture PDFs with pymupdf at test time |
| `tests/test_*.py` | one per module |
| `README.md` | quickstart and the agent contract |

Dependency direction is strictly one-way: `cli` → `commands` → {`ingest`, `render`, `instructions`, `workdir`} → {`figures`, `naming`, `errors`}. Nothing imports `cli`.

---

