# Task 2 report: Instructions tell agents to write LaTeX

## What I implemented

Per `task-2-brief.md`:

1. Replaced `test_no_unreplaced_placeholders` in `tests/test_instructions.py` with
   the four tests the brief specifies verbatim: the updated
   `test_no_unreplaced_placeholders` (now checks for `{{`/`}}` instead of `$`),
   `test_equations_are_latex`, `test_no_plain_text_equation_wording`, and
   `test_values_containing_braces_or_dollars_are_inserted_verbatim`.
2. Replaced `src/lecnotes/instructions.py`: swapped `string.Template`
   `$name` substitution for a regex-based single-pass `{{name}}` substitution
   (`_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")`), exactly as given in the brief.
3. Updated `src/lecnotes/templates/instructions.md`:
   - `$deck` → `{{deck}}` (title line and the `out/$deck.md` line)
   - `$source_name` → `{{source_name}}`
   - `$slides` → `{{slides}}`
   - Replaced the whole `### Equations` section (heading through the paragraph
     before `### Going beyond the slides`) with the exact Markdown block given in
     the brief, teaching `$...$` inline math, `$$` display blocks, escaping `\$`,
     and never using code spans/blocks for math.
   - Left every other line of the template unchanged.

## TDD evidence

RED — after Step 1 (test changes only, before touching `instructions.py` or the
template):

```
uv run pytest tests/test_instructions.py -v
```

```
tests/test_instructions.py::test_equations_are_latex FAILED
tests/test_instructions.py::test_no_plain_text_equation_wording FAILED
...
2 failed, 13 passed in 0.03s
```

`test_equations_are_latex` failed because the template still had no
`$\pi_\theta(a_t \mid s_t)$`, no `$$` display block, etc. (the old template used
plain-text equation wording). `test_no_plain_text_equation_wording` failed
because the old `### Equations` section literally contained
"Type every equation as plain text". Both failures were for the expected
reason — the implementation (instructions.py + template) had not yet been
updated. The other 3 new/changed tests unexpectedly passed at this point:
`test_no_unreplaced_placeholders` (no `{{`/`}}` present yet, trivially true) and
`test_values_containing_braces_or_dollars_are_inserted_verbatim` (still true
under the old `string.Template`, since braces/dollars in argument values were
never treated as placeholder syntax either).

GREEN — after Step 3 (new `instructions.py`) and Step 4 (template rewrite):

```
uv run pytest tests/test_instructions.py tests/test_prep.py -v
```

```
tests/test_instructions.py::test_states_the_deck_and_slide_count PASSED
...
tests/test_instructions.py::test_equations_are_latex PASSED
tests/test_instructions.py::test_no_plain_text_equation_wording PASSED
tests/test_instructions.py::test_values_containing_braces_or_dollars_are_inserted_verbatim PASSED
...
tests/test_prep.py::test_written_instructions_say_to_finish_from_inside_the_workdir PASSED
============================== 35 passed in 0.68s ==============================
```

Full suite:

```
uv run pytest -q
```

```
302 passed in 4.92s
```

No warnings.

## Test count

- Before: 299 passed (verified with `uv run pytest -q` prior to any change).
- After: 302 passed (net +3: removed 1 old test, added 4 new tests → +3).

## Files changed

- `src/lecnotes/instructions.py` — regex `{{name}}` substitution, replacing
  `string.Template`.
- `src/lecnotes/templates/instructions.md` — placeholders updated to `{{...}}`;
  `### Equations` section rewritten to teach LaTeX. All other wording unchanged.
- `tests/test_instructions.py` — `test_no_unreplaced_placeholders` replaced with
  the brief's four tests.

Commit: `5866bb4` "Tell agents to write equations as LaTeX" (only these three
files staged; the untracked `docs/` report from Task 1 was left alone and
nothing under `docs/` was committed).

## Deviations from the brief

None. `instructions.py`, the test additions, and the `### Equations` replacement
block were copied verbatim from the brief; the three placeholder renames were
mechanical `$name` → `{{name}}` substitutions at the three call sites the brief
named (title line, source-material line, and the final `out/$deck.md` line).

## Self-review findings

- Diffed the change against the brief's literal blocks (`instructions.py`,
  the test additions, the Equations replacement) — byte-for-byte match.
- Grepped the repo for any other reference to `string.Template`, `$deck`,
  `$slides`, `$source_name`, or callers of `render_instructions` — only
  `src/lecnotes/commands.py`'s existing call (`render_instructions(deck=...,
  slides=..., source_name=...)`) remains, and its call signature/kwargs are
  unaffected by this change.
- Confirmed `git status` shows only the three intended files staged before
  committing (the untracked Task 1 report under `docs/` was left untouched,
  and nothing under `docs/` was committed).
- Ran the full suite once more after committing: 302 passed, no warnings.

## Concerns

None.
