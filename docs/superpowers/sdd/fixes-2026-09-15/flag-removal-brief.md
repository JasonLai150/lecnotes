# Remove the per-slide figure flag everywhere; install the new INSTRUCTIONS.md

Repo: /Users/jasonlai150/Documents/GitHub/lecnotes (Python, uv; `uv run pytest`).
This lands after the caption-bracket fix, which already switched figure-link parsing to markdown-it-py.

## Why
`render.has_figure` flags a slide when it has a large embedded image or >12 vector drawings. On real decks it fired on 46/52, 60/69 and 44 slides — no signal — and it changes no behavior. Its only effect was on the writing agent, via INSTRUCTIONS.md calling it "a hint telling you which ones repay a close look", which invites skipping images on unflagged slides. The real risk is equations and whole slides existing only as images, which the flag cannot detect. Decision (user-approved): remove it everywhere, and tell the agent to view every slide image.

## Changes
1. `src/lecnotes/render.py`: delete `FIGURE_IMAGE_AREA`, `FIGURE_DRAWING_COUNT`, `has_figure`; manifest page rows become `{"n", "png", "txt", "chars"}`.
2. `src/lecnotes/commands.py` (`prep`): drop the top-level `"figures"` manifest key and the `"figures"` key in the result dict; stop passing figures to `render_instructions`.
3. `src/lecnotes/instructions.py`: `render_instructions(deck, slides, source_name)` — remove the `figures` parameter.
4. `src/lecnotes/cli.py`: prep human output says `N slides` (no "with figures").
5. `src/lecnotes/templates/instructions.md`: replace the whole file with the approved draft at `docs/superpowers/sdd/fixes-2026-09-15/instructions-template-draft.md`, verbatim. It uses only the placeholders `$deck`, `$slides`, `$source_name`.
6. README.md: remove `"figures":…` from the JSON example and "including which slides carry figures" from the layout description; if README describes the pages files, make it consistent with the new wording (every slide image is viewed; .txt can be incomplete). Don't restructure the README otherwise.
7. Old workdirs whose manifests still contain `figure`/`figures` must keep working with `finish` (they do if nothing reads those keys — add a test that `finish` succeeds on a manifest carrying the old keys).

Leave `figures.py`, `out/figures/`, `figures_resolved`, and figure-link validation alone — "figure" there means a linked slide image, which stays.

## Tests (update first, watch them fail, then change code)
- test_render.py: remove the has_figure tests and `figure` assertions; assert rows have exactly keys n/png/txt/chars.
- test_prep.py: manifest has no `figures` key and pages have no `figure` key; result dict has no `figures` key.
- test_instructions.py: update the `render_instructions` call; assert the rendered text contains "View every slide image", "Beyond the slides", "pseudocode", "source.pdf", the original source name, contains no `figure` flag wording ("repay a close look", "hint, not a filter") and no leftover `$`.
- test_cli.py: prep human output no longer mentions "with figures"; JSON has no `figures`.
- test_finish.py: finish works on a workdir whose manifest still has the old `figures`/`figure` keys.
Grep afterwards: `grep -rn "has_figure\|FIGURE_\|with figures\|carry figures" src tests README.md` must return nothing.

## Constraints
- Commit on main (one or two commits), do NOT push, do not commit anything under docs/superpowers/sdd/.
- Commit messages end with `Co-Authored-By: Claude <your model name> <noreply@anthropic.com>` then `Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy`.
- Full suite passes with no warnings.
