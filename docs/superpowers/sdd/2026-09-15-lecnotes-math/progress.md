# SDD ledger — plan: docs/superpowers/plans/2026-09-15-lecnotes-math.md

Spec: docs/superpowers/specs/2026-09-15-lecnotes-math-design.md (binding), extending the base and export specs.
Start commit: see first Progress line. Suite before: 291 passing.

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

- Ruling: KaTeX render script uses `katex.render` per element rather than KaTeX's auto-render contrib — one fewer vendored file, and the markup is ours — cost if wrong: none.
- Ruling: Implementers — sonnet for all five tasks (new library, vendoring with integrity check, render rules); reviewers sonnet; final review opus — cost if wrong: modest extra spend.

## Deferred minors

## Progress
