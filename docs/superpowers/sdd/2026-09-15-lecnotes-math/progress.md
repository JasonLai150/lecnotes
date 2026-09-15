# SDD ledger — plan: docs/superpowers/plans/2026-09-15-lecnotes-math.md

Spec: docs/superpowers/specs/2026-09-15-lecnotes-math-design.md (binding), extending the base and export specs.
Start commit: 8bdef0f. Suite before: 291 passing.

## Pre-flight scan

| Tasks | Interface | Finding |
|---|---|---|
| T1 → T4, T5 | `new_parser()` with dollarmath; `inline_text(children)` | OK |
| T3 → T4 | `katex_css()`, `katex_js()` | OK |
| T2 | template placeholders `{{name}}`; `render_instructions` signature unchanged | OK — prep's call site unchanged |
| T4 existing tests | `test_page_shell_is_self_contained` forbids `<script`/`http` | OK — its document has no math, KaTeX not included |
| T5 | Notion title with math → backslash sanitized to `-` | Plan test expectation set to `The -pi policy` (preflight fix) |
| Self-review | three plan tests would have failed for the wrong reason | Fixed before dispatch: price/space/code cases split into paragraphs; dropped a `renderMathInElement` assertion that depends on KaTeX internals; Notion title expectation |

## Rulings

- Ruling: Per the user's new preference, no per-task ledger commits and no per-task pushes: one code commit per task, the ledger/reports in one docs commit, and a single push when the feature is done — cost if wrong: nothing reaches GitHub until the end.

- Ruling: KaTeX render script uses `katex.render` per element rather than KaTeX's auto-render contrib — one fewer vendored file, and the markup is ours — cost if wrong: none.
- Ruling: Implementers — sonnet for all five tasks (new library, vendoring with integrity check, render rules); reviewers sonnet; final review opus — cost if wrong: modest extra spend.

- Ruling: Task 2 review Important (plan-mandated) — the indented `$$` example in INSTRUCTIONS.md can be copied with its indentation, which parses as an indented code block and renders as raw LaTeX. Fix: state that `$$` lines go flush left and the indentation only marks the example, with a test; folded into Task 5's commit per the user's fewer-commits preference, and verified by Task 5's review instead of a separate fix round — cost if wrong: Task 2 stays open until Task 5 lands.

- Ruling: Task 4 review — (1) `math_inline_double` renders as `<span class="lecnotes-math lecnotes-math-display">` styled `display: block`, reserving `<div>` for `math_block`; the plan's `<div>` inside `<p>` made browsers split the paragraph. (2) Fix the dollar-math plugin leaking blockquote `>` markers into `math_block` content with a core rule in `mdparse.new_parser` that strips one leading `>` marker per enclosing blockquote from each content line, so finish, HTML, and any future consumer see clean LaTeX; blockquote math is likely because INSTRUCTIONS.md encourages 'Beyond the slides' callouts — cost if wrong: a core rule we maintain around a plugin quirk.

- Ruling: Final review — one fix commit for Important 1-3 (allow_blank_lines=False; table-cell pipe guidance; stale no-JS wording) plus minors 1, 3, 4, 6, 7 (alt text keeps math; no math in # title; list-item $$ indentation; display margin; spec wording); minors 2 and 5 to BACKLOG — all reproduced by the reviewer on a realistic DRL document — cost if wrong: two more sentences in INSTRUCTIONS.md.

## Deferred minors
- Task 1: minor (deferred): no test that allow_labels=False keeps `$$...$$ (label)` from producing math_block_label.

## Progress
- Task 1: complete (commits 8bdef0f..077b979, review clean; literal $ in prose, tables, links, and inline_text on nested formatting verified)
- Task 2: review Needs fixes (1 Important, plan-mandated: indented $$ example) — fix folded into Task 5 per ruling
- Task 3: complete (commits 5866bb4..d736a1f, review clean; vendored files byte-identical to npm katex 0.18.7; ⚠️ wheel fonts resolved by controller: wheel ships all 20 woff2)
- Task 2: complete (commits 077b979..5866bb4 + fix in 2b6d705; flush-left finding ADDRESSED, verified on a rendered INSTRUCTIONS.md)
- Task 5: complete (commits 4ab146f..2b6d705, review clean)
- Task 4: review Needs fixes — math_inline_double <div> inside <p>; blockquote `>` leaking into math_block content; fix round 1 dispatched
- Task 4: fix round 1/5 (2 addressed, 0 open — inline $$ as <div> in <p>; blockquote markers in math_block; commit 2b6d705..b9618b5; verified in headless Chrome, Notion passthrough unaffected)
- Task 4: complete (commits d736a1f..4ab146f + b9618b5, review clean after 1 fix round)
- Final review: With fixes — 0 critical, 3 important, 8 minor (8bdef0f..b9618b5). One fix commit per final-fix-brief.md.
- Final fix: 1 commit b9618b5..17aac81; scoped re-review: items 1-6 ADDRESSED, no new breakage; 335 tests passing, no warnings. mdit-py-plugins>=0.4 floor kept — controller verified allow_blank_lines exists in 0.4.0, 0.4.1, 0.4.2, 0.5.0, 0.6.1.
