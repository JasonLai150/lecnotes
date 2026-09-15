# Task 9 Report: The instructions template

## Summary

Successfully implemented Task 9, creating the agent-facing instructions template system. The implementation includes:

1. A Markdown template (`src/lecnotes/templates/instructions.md`) using `string.Template` for safe substitution of 5 placeholders
2. A Python loader module (`src/lecnotes/instructions.py`) providing the `render_instructions()` function
3. A comprehensive test suite (`tests/test_instructions.py`) with 6 tests verifying all functionality

The implementation follows TDD methodology exactly as specified in the brief.

## What was implemented

### Files created:
- `src/lecnotes/templates/__init__.py` (empty package marker)
- `src/lecnotes/templates/instructions.md` (the Markdown template with 5 placeholders: $deck, $source_name, $slides, $figures, $workdir_name)
- `src/lecnotes/instructions.py` (the render_instructions() function)
- `tests/test_instructions.py` (6 tests)

### The `render_instructions()` interface:
```python
def render_instructions(
    deck: str, slides: int, figures: int, source_name: str, workdir_name: str
) -> str
```

Loads the template from package resources and substitutes the 5 placeholders using `string.Template`, which safely leaves all Markdown braces, backticks, and other special characters untouched.

## TDD Evidence

### Step 1-2: RED - Initial test failure
```bash
$ uv run pytest tests/test_instructions.py -v
```

Output:
```
ERROR tests/test_instructions.py
E   ModuleNotFoundError: No module named 'lecnotes.instructions'
```

Expected: FAIL due to missing module ✓

### Step 5: Template resource verification
```bash
$ uv run python -c "from importlib.resources import files; print(len(files('lecnotes.templates').joinpath('instructions.md').read_text()))"
```

Output: `1776` (non-zero character count, template loads successfully) ✓

### Step 6: GREEN - All tests passing
```bash
$ uv run pytest tests/test_instructions.py -v
```

Output:
```
tests/test_instructions.py::test_states_the_deck_and_counts PASSED       [ 16%]
tests/test_instructions.py::test_shows_the_exact_figure_link_syntax PASSED [ 33%]
tests/test_instructions.py::test_names_the_file_to_write PASSED          [ 50%]
tests/test_instructions.py::test_names_the_command_to_run_when_done PASSED [ 66%]
tests/test_instructions.py::test_points_at_both_the_png_and_the_txt PASSED [ 83%]
tests/test_instructions.py::test_no_unreplaced_placeholders PASSED       [100%]

======================== 6 passed, 5 warnings in 0.01s =========================
```

All 6 tests pass ✓

### Full test suite verification
```bash
$ uv run pytest --collect-only -q
```

Output: `64 tests collected in 0.01s` (58 existing + 6 new) ✓

```bash
$ uv run pytest -v
```

Output: `======================== 64 passed, 5 warnings in 0.34s =========================` ✓

## Files changed

### Created files:
1. `/Users/jasonlai150/Documents/GitHub/lecnotes/src/lecnotes/templates/__init__.py`
   - Empty package marker file (0 bytes)

2. `/Users/jasonlai150/Documents/GitHub/lecnotes/src/lecnotes/templates/instructions.md`
   - Markdown template (1776 characters)
   - Contains 5 placeholder fields: $deck, $source_name, $slides, $figures, $workdir_name
   - Includes example of figure-link syntax as indented code block
   - Specifies NOTES.md as output filename
   - Specifies "lecnotes finish $workdir_name" as the completion command
   - References both pages/slide-NNN.png and pages/slide-NNN.txt file formats

3. `/Users/jasonlai150/Documents/GitHub/lecnotes/src/lecnotes/instructions.py`
   - Uses importlib.resources for package resource loading
   - Uses string.Template for safe placeholder substitution
   - Function signature exactly matches brief specification

4. `/Users/jasonlai150/Documents/GitHub/lecnotes/tests/test_instructions.py`
   - 6 tests verifying all aspects of render_instructions():
     - test_states_the_deck_and_counts: Verifies deck name, slide count, figure count appear in output
     - test_shows_the_exact_figure_link_syntax: Verifies exact figure link syntax
     - test_names_the_file_to_write: Verifies "NOTES.md" appears
     - test_names_the_command_to_run_when_done: Verifies "lecnotes finish" command
     - test_points_at_both_the_png_and_the_txt: Verifies file paths reference both PNG and TXT files
     - test_no_unreplaced_placeholders: Verifies all placeholders were replaced (strict $ check)

## Deviations from the brief

None. All implementation details match the brief exactly:
- Template text copied verbatim with exact indentation
- Five placeholders placed exactly as shown
- Figure-link example maintained as 4-space indented code block
- Function signature and implementation exactly as specified
- Test suite identical to brief specification
- No modifications to pyproject.toml (confirmed per brief note)

## Self-review findings

### Completeness ✓
- All 6 tests from brief included and passing
- All 5 placeholders properly substituted
- Template loads correctly via importlib.resources
- Full test suite expanded from 58 to 64 tests as required
- No edge cases missed

### Code quality ✓
- Clear, concise implementation
- No unnecessary complexity
- Docstring provided for instructions.py explaining why string.Template is used
- Follows project naming conventions and structure
- Proper package resource isolation (files under lecnotes.templates)

### Discipline (YAGNI) ✓
- No configuration added (as noted in brief that this is for later tuning)
- No extra functions or modules
- Only the required render_instructions() function
- Minimal, focused implementation

### Testing ✓
- TDD methodology followed exactly
- All tests in brief implemented identically
- Tests verify actual behavior (not just placeholder existence)
- No assertions weakened
- Full suite (64 tests) passes cleanly

## Concerns

None. The implementation is complete, tested, and ready for integration.

## Commit information

Commit: `ab1d8c2` "Add the agent-facing instructions template"

All changes properly staged and committed with required attribution lines.
