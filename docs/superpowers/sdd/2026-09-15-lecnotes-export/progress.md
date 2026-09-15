# SDD ledger — plan: docs/superpowers/plans/2026-09-15-lecnotes-export.md

Spec: docs/superpowers/specs/2026-09-15-lecnotes-export-design.md (+ "Amendments during planning"), extending docs/superpowers/specs/2026-08-27-lecnotes-design.md (+ amendments). Reachable, binding.
Repo: https://github.com/JasonLai150/lecnotes (public), branch main
Start commit: 56e7d47 (189 tests passing)

## Pre-flight scan

### Shared files / interfaces

| Tasks | Produces → consumes | Finding |
|---|---|---|
| T1 → T2, T3, T4 | `mdparse.new_parser()`, `PARSER`, `inline_tokens(md, parser=PARSER)` | OK |
| T1 ↔ existing figures.py | `_iter_link_tokens` rebuilt on `inline_tokens`; parser gains table+strikethrough | OK — images inside table cells still parse as inline images; figure tests must stay green |
| T2 → T3, T4, T5 | `IMAGE_TYPES`, `is_external`, `LocalImage(src, path).mime`, `local_images`, `missing_images`; conftest `make_png` / `png` | OK |
| T3 → T5 | `render_html(markdown, base_dir, title_fallback) -> str` | OK |
| T4 → T5 | `images_outside(images, base_dir) -> list[str]`, `write_notion_zip(markdown, images, base_dir, dest, fallback_stem)` | OK |
| T5 ↔ tests/test_cli.py guard | new raise sites make `test_every_raised_error_code_has_a_cli_scenario` fail until Step 5 of the same task | OK — intra-task, stated in the plan |
| T5 → T6 | CLI `export` | OK |

### Per-task self-consistency

| Task | Tests vs code vs files | Finding |
|---|---|---|
| T1 | 5 tests; code spans/fence/indented code excluded | OK |
| T2 | 10 tests; `unquote` for `<figures/my slide.png>` | OK |
| T3 | 14 tests; figure detection via paragraph meta; tight-list exclusion | OK (markdown-it render-rule API flagged as possible deviation point) |
| T4 | 12 tests; hand-traced unwrap hard-break and list cases, sanitize expected string, zip dedupe | OK |
| T5 | 13 command tests + 4 CLI tests + 3 scenarios | `from conftest import make_png` import risk; plan gives fallback |
| T6 | e2e on a scratch copy of the user's DRL workdir | OK — never touches the user's workdir |

## Rulings

- Ruling: Continue committing directly on `main` and pushing after each reviewed task — same authorization as the first build — cost if wrong: no PR history.
- Ruling: Implementer models — haiku for T1, T2 (complete code, small); sonnet for T3, T4, T5 (markdown-it API details may diverge) and T6 (real-data verification); reviewers sonnet; final review opus — cost if wrong: an escalation round.

- Ruling: Task 5 review — `-o` resolving to the input Markdown itself, or to an existing directory, raises a new code `invalid_output` (exit 1) before anything is written — the reviewer reproduced `-o <input.md>` silently overwriting the source of truth with HTML, and `-o <dir>` crashing with a traceback; one code covers both because both mean 'this output path cannot be written' — cost if wrong: one more error code in the contract.

- Ruling: Final review — fix wave covers Important 1-3 (samefile-based output identity incl. NOTES.md in workdir mode and parent-is-a-file; not_finished wording offering both remedies) plus minors: Notion title sanitizing (colon → ' - ', whitespace/control chars), zip entry names from normalized src with lexical outside-root check, tmp cleanup, HTML title top-level H1, image_not_found reasons, case-insensitive slide shape in finish, stale wording — all reproduced by the reviewer; the colon one hits every real lecture title — cost if wrong: small spec surface changes, recorded in the export spec's final-review amendments.
- Ruling: Deferred — blockquote paragraph unwrapping, error-code mapping for non-UTF-8 sources/unreadable images, find_malformed double-listing — not reproduced on real notes or cosmetic — cost if wrong: a hard-wrapped callout shows literal asterisks in Notion; an unreadable file gives internal_error.

- Ruling: Accept fix-wave deviations — parent-is-a-file check walks to the nearest existing ancestor (also catches `-o file/sub/out.html`); HTML data-URI MIME follows the link's extension like `LocalImage.mime` (prevents a KeyError on a `.png` symlink to a `.bin`) — both strict improvements consistent with the amendments — cost if wrong: none.
- Ruling: Parked to docs/BACKLOG.md — export result `images` counts distinct target files; sanitize can leave a double space around a dropped control character — cosmetic — cost if wrong: a slightly-off count in JSON; a double space in a Notion page title.
- Ruling: Keep this plan's SDD workspace committed under docs/superpowers/sdd/ (user asked for agent docs in docs/); only untracked review-*.diff scratch removed — cost if wrong: extra process files.

## Deferred minors

- pre-plan (bracket-fix review): `find_malformed` can list one bad link twice when the link's own text also contains `slide-NNN.png` (e.g. `[see slide-021.png](figures/slide-021.png)` → href and text fragment). Cosmetic; correctness holds.
- pre-plan (flag removal): `tests/conftest.py` deck_47 comment still says "slide 8 carries a figure".
- Task 1: minor (deferred): mdparse.py lost the note on why reusing one parser instance is safe; no finish-level test of a figure link inside a pipe table (covered one layer down in test_mdparse).
- Task 2: minor (deferred): test_image_types checks 3 of 6 MIME entries; no test for a filesystem-absolute image src (e.g. /abs/x.png).
- Task 3: minor (deferred): title extraction uses tokens[i+1].children without the `or []` guard used elsewhere; no test for a figure paragraph inside a loose list or blockquote (verified correct manually).
- Task 4: minor (deferred): no regression tests for absolute image src in images_outside, setext heading / paragraph-then-list / no-trailing-newline unwrap cases, non-ASCII zip titles (all verified correct manually); a whitespace-only `#` heading falls back to the stem but stays in the body; duplicate Path(base_dir).resolve().
- Task 6: minor (deferred): Notion page title sanitization turns `Learning from Data: Imitation...` into `Learning from Data- Imitation...` (colon → `-` with no space) — visible as the Notion page title.

## Progress
- Task 1: complete (commits f4407ff..7e83b78, review clean)
- Ruling: Controller amended Task 2's commit message (827d5d8, formerly fdf0806) before push — the implementer put the trailer lines on the subject line; code unchanged — cost if wrong: none.
- Task 2: complete (commits 7e83b78..827d5d8, review clean; ⚠️ absolute-path src resolved: pathlib join discards base_dir, but images_outside compares the resolved absolute path with is_relative_to(base), so it is flagged for notion like ../ — final review to confirm with a test)
- Task 3: complete (commits 827d5d8..b84a183, review clean; escaping, post-parse data URIs, and nested figures verified by reviewer)
- Task 4: complete (commits 338d2fb..ce74d37, review clean; ⚠️ commands wiring of images_outside before write_notion_zip confirmed in Task 5's code)
- Task 5: review Needs fixes — 1 Critical (-o equal to the input .md overwrites the source), 1 Important (-o existing directory → traceback); fix round 1 dispatched
- Task 6: complete (commits 8cc1c75..0d193bc, review clean; real export of CS 8803 lec 1: 20/20 figures embedded in 8.5 MB HTML, 6.3 MB zip)
- Task 5: fix round 1/5 (2 addressed, 0 open — -o == source overwrote Markdown; -o directory traceback; commits 0d193bc..c503277)
- Task 5: complete (commits 338d2fb..c503277, review clean after 1 fix round; symlink and ..-relative -o verified)
- Final review: With fixes — 0 critical, 3 important, 9 minor (56e7d47..5671b0c). One fix wave per final-fix-brief.md.
- Final fix wave: 4 commits 57aca23..c5e279a; scoped re-review: all 10 findings ADDRESSED, deviations a-d accepted, no new breakage; 291 tests passing, no warnings.
