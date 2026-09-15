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

- Ruling: Co-Authored-By trailer names the model that actually authored each commit (e.g. Claude Sonnet 5 for sonnet implementers) instead of a fixed Opus line — Task 3's implementer followed its own harness attribution, which is the accurate one — cost if wrong: trailers vary by commit.

- Ruling: Task 9 keeps `src/lecnotes/templates/__init__.py` although the plan said add it only if the resource failed to load without it — the reviewer showed it loads without it under the editable install, but a regular package is the robust choice for importlib.resources across install modes (wheel, zipimport, older importlib namespace-package handling); the plan's conditional was the defect, not the file — cost if wrong: one empty file.

- Ruling: Task 12 argparse usage errors must exit 1, not argparse's default 2 — the spec binds exit 2 to missing external dependencies, and the plan's verbatim CLI code let argparse leak SystemExit(2) for missing args / unknown subcommands; `--help` and `--version` keep exit 0 — cost if wrong: none; an agent branching on exit 2 would otherwise tell users to install LibreOffice after a typo.

- Ruling: Final review — amend the spec rather than defend it on seven gaps it had: install via `uv tool install`; INSTRUCTIONS tells agents `lecnotes finish .`; shell-quoted `next`; Unicode-aware slug with `deck` fallback; content-validated workdir identity; prep validates input before touching disk (new codes `source_not_found`, `invalid_pdf`); malformed figure links rejected (`figure_malformed`); JSON errors carry `message`; `internal_error` in --json mode; `\d{3,}` slide numbers — each reproduced by the final reviewer, most would bite the first real agent run — cost if wrong: four new error codes and a manifest-shape check in the contract.
- Ruling: Final-review minors fixed in the same wave: SameFileError on self-source --force, soffice stderr in conversion_failed, sdist excludes sdd docs, SWIG warnings filtered, slug→output e2e test. Left as-is: layout literals outside workdir.py, deck_47 fixture, version duplication, symlinked pages/, all other deferred minors per the reviewer's triage — cost if wrong: small cleanup debt.

- Ruling: Accept fix-wave deviation — strict figure regex is `slide-(\d{3}|[1-9]\d{3,})\.png` instead of `\d{3,}` — `slide-0001.png` would otherwise validate but point at a file finish never writes — cost if wrong: an agent writing 4-digit zero-padded links gets figure_malformed instead of success.
- Ruling: Parked — re-prepping from a workdir's own `source.pdf` succeeds but renames the deck to `source` (output becomes `out/source.md`); real but rare, previously a crash, nothing downstream builds on it; fix later by keeping the existing manifest's deck name under --force — cost if wrong: a user doing exactly that gets a misnamed output file.
- Ruling: Parked — a `.pptx` targeting an existing workdir without --force runs the soffice conversion before the workdir_exists check; wasted work, nothing written — cost if wrong: a few seconds of conversion.
- Ruling: Keep the SDD workspace (ledger, briefs, reports) committed under docs/superpowers/sdd/ instead of deleting it at finish — user asked for all agent docs in a docs directory; only the untracked review-*.diff scratch files are removed — cost if wrong: ~30 process files in docs/, removable in one commit.

## Deferred minors


- preflight: `workdir.OUT_FIGURES` constant is defined but `out_figures_dir()` builds the path from `OUT` + "figures" literally.
- preflight: INSTRUCTIONS.md says `lecnotes finish <workdir name>`, which only works if the agent's cwd is the workdir's parent; an agent cd'd into the workdir needs `lecnotes finish .`. Editorial-template territory (deferred by spec).
- Task 1: minor (deferred): pyproject console script points at lecnotes.cli before T12 creates it (expected forward reference).
- Task 2: minor (deferred): implementer report described a function docstring that isn't in the committed code (report accuracy only).
- Task 3: minor (deferred): fixtures have no embedded-image key, so the image-area (>40,000px) branch of has_figure is untested by any planned test.
- Task 6: minor (deferred): plan File Structure table lists workdir.create() but no brief defines or calls it; table is stale.
- Task 8: minor (deferred, plan-mandated): (a) duplicated no-such-file guard in .pdf and .pptx branches of resolve_source; (b) test_pptx_conversion_success never asserts the soffice command shape; (c) conversion_failed discards soffice stderr, so real failures carry no diagnostic.
- Task 9: minor (deferred): implementer report claimed no deviations while adding templates/__init__.py unconditionally (report accuracy).
- Task 10: minor (deferred): (a) unused 'import json' in tests/test_prep.py; (b) prep --force removes pages/ before render_deck, so a render failure mid-way leaves an existing workdir with no pages/ (no atomicity).
- Task 11: minor (deferred): no test for finish when NOTES.md was deleted after prep (missing-file branch).
- Task 12 / suite-wide: minor (deferred): pytest output carries 5 DeprecationWarnings from pymupdf's SWIG bindings (SwigPyPacked/SwigPyObject/swigvarlink has no __module__), present since pymupdf was first imported; not pristine — could filter in [tool.pytest.ini_options].

## Progress
- Task 1: complete (commits be1f4fd..263ad3e, review clean)
- Task 2: complete (commits e9a6408..fe7a65b, review clean)
- Task 3: complete (commits 25706ef..1bf4c21, review clean)
- Task 4: complete (commits b32a8cd..a1be34d, review clean; deviation: crop_render rescales when pymupdf outward pixel rounding yields 1401px — reviewer reproduced and stress-tested; ⚠️ find_refs confirmed scheduled in Task 5)
- Task 5: complete (commits e09d315..dd45b95, review clean)
- Task 6: complete (commits 49e71db..7156123, review clean)
- Task 7: complete (commits 8664e53..5296c99, review clean; reviewer confirmed full-page renders never hit the 1401px rounding across 2000 random page sizes)
- Task 8: complete (commits f462831..d4fcd6e, review clean)
- Task 9: complete (commits f0a57de..ab1d8c2, 1 Important finding ruled on: keep templates/__init__.py, plan amended)
- Task 10: complete (commits 02865ca..2b89564, review clean)
- Task 11: complete (commits 43042b8..dae21a1, review clean)
- Task 12: fix round 1/5 (1 addressed, 0 open — argparse usage errors exited 2; commits 280b517..c15c6e1)
- Task 12: complete (commits ba0f4f3..c15c6e1, review clean after 1 fix round)
- Task 13: complete (commits 126b515..8590591, review clean; ⚠️ README corpus stats resolved: match 4440 README's 1,226/1,240 text-layer and 758 figure counts)
- Final review: With fixes — 0 critical, 7 important, 10 minor (e8bf4ef..ec5b3ff). One fix wave dispatched per final-fix-brief.md.
- Final fix wave: 7 commits b2dabb4..085db76, scoped re-review: all 12 findings ADDRESSED, no new Critical/Important breakage; 177 tests passing, no warnings.
