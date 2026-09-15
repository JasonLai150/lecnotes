# SDD ledger — plan: docs/superpowers/plans/2026-08-27-lecnotes.md

Spec: docs/superpowers/specs/2026-08-27-lecnotes-design.md (reachable, binding)
Repo: https://github.com/JasonLai150/lecnotes (public), branch main
Start commit: e8bf4ef

## Pre-flight scan

### Shared files / interfaces

| Tasks | Produces → consumes | Finding |
|---|---|---|
| T1 → T9 | pyproject `packages=["src/lecnotes"]` → template loaded via importlib.resources | OK; T9 has the `__init__.py` fallback |
| T1 → all | `LecnotesError(code,msg,**detail)`, `.exit_code`, `.to_dict()` → T6, T8, T10, T11, T12 | OK, names match |
| T2 → T8 | `slugify(str)->str` → `resolve_source` | OK |
| T3 → T4, T7, T8, T10, T11, T12 | `synth(path, specs)` keys text/drawing/many_lines/backdrop/small_box/blank | **Defect:** `drawing` described as tripping the figure heuristic, but it's one drawing (needs >12); `deck_47` slide 8 comment was false. Fixed in plan |
| T4 → T7 | `TARGET_LONG_EDGE` → render.py | OK |
| T4, T5 → T11 | `crop_render(pdf, slide, dest)`, `find_refs(md)->list[int]` → finish | OK |
| T6 → T7, T10, T11 | `page_png/page_txt/rel_png/rel_txt`, `notes_path`, `out_figures_dir`, `is_workdir`, `require_workdir`, `INSTRUCTIONS` | OK. `OUT_FIGURES` constant unused by `out_figures_dir` (minor) |
| T8 → T10 | `SourceInfo.pdf/deck/source_name/source_format/converted` | OK; T10 uses tmpdir PDF only inside the `with` block |
| T9 → T10 | `render_instructions(deck, slides, figures, source_name, workdir_name)` | OK |
| T10 → T11 | `NOTES_STUB` | OK |
| T10, T11 → T12 | `prep(...)`, `finish(root)` result dicts | OK, keys match reporters |
| T12 tests | capsys | **Defect:** 3 tests call `prep` (prints to stdout) then `finish`, and read capsys once → prep output pollutes; `json.loads` fails / `out == ""` fails. Fixed in plan |

### Per-task self-consistency

| Task | Tests vs code vs files | Finding |
|---|---|---|
| T1 | 10 tests; `git add uv.lock` produced by `uv sync` | OK |
| T2 | 7 tests | OK |
| T3 | 5 tests | see `drawing` defect above |
| T4 | 7 tests; approx coords | OK |
| T5 | 7 tests; says move `import re` to top | OK |
| T6 | 7 tests | OK |
| T7 | 7 tests | OK |
| T8 | 8 tests; missing-file check precedes `which` | OK |
| T9 | 6 tests; Step 5 verify only | OK |
| T10 | 11 tests | **Safety gap:** `--force` on an existing non-workdir directory rmtrees its `pages/`. Added guard + test (now 12) |
| T11 | 10 tests | OK |
| T12 | 9 tests | capsys defect above |
| T13 | writes to /tmp | moved to session scratchpad |
| Global | "no co-author trailer" vs harness attribution rules | conflict, ruled below |

## Rulings

- Ruling: Work directly on `main` in the new repo, no worktree/feature branch — user created a fresh solo repo and asked for commits as I implement — cost if wrong: history is on main instead of a PR branch; trivially reorganizable before anyone else depends on it.
- Ruling: Push to origin/main after each task's review passes — user asked for a public repo with commits as I go — cost if wrong: unreviewed-by-human code is public early; repo is new and unused.
- Ruling: SDD workspace (ledger, briefs, reports) lives at `docs/superpowers/sdd/2026-08-27-lecnotes/` and is committed, instead of the git-ignored `.superpowers/sdd/` — user asked for all agent docs in a docs directory — cost if wrong: ~13 briefs + reports of clutter in docs/, deletable in one commit. Review-package diffs are git-ignored because they duplicate git history.
- Ruling: T3 `drawing` key description corrected and `deck_47` slide 8 uses `many_lines: 20` — plan's comment claimed a figure the heuristic wouldn't detect — cost if wrong: none; fixture only asserts page count.
- Ruling: T10 `prep --force` refuses (`workdir_exists`) when the target exists but is not a workdir — spec only covers re-rendering a workdir; the plan's code would `rmtree` a `pages/` folder inside any directory passed to `-o` — cost if wrong: user can't `--force` into a pre-existing non-workdir directory and must pick a fresh path.
- Ruling: T12 tests discard prep's captured output with `capsys.readouterr()` before exercising finish — as written, three tests would fail on output pollution, not on behavior — cost if wrong: none.
- Ruling: Commits carry the Co-Authored-By / Claude-Session trailer, overriding the plan's "no trailer" line — harness attribution rules outrank plan text — cost if wrong: two extra lines per commit message.
- Ruling: T13 end-to-end output goes to the session scratchpad instead of /tmp — environment rule — cost if wrong: none.
- Ruling: Implementer models — haiku for pure-transcription tasks (T1, T2, T5, T6, T9); sonnet where pymupdf behavior may diverge from the plan's code and need debugging (T3, T4, T7, T8, T10, T11, T12) and for T13's judgment-based e2e check. Reviewers sonnet; final review opus — cost if wrong: extra turns or an escalation round.

## Deferred minors

- preflight: `workdir.OUT_FIGURES` constant is defined but `out_figures_dir()` builds the path from `OUT` + "figures" literally.
- preflight: INSTRUCTIONS.md says `lecnotes finish <workdir name>`, which only works if the agent's cwd is the workdir's parent; an agent cd'd into the workdir needs `lecnotes finish .`. Editorial-template territory (deferred by spec).

## Progress
