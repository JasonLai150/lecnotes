# Task 6 Implementation Report

## Summary
Implemented the workdir layout module (`src/lecnotes/workdir.py`) and its test suite (`tests/test_workdir.py`). This module provides a single source of truth for all workdir folder layout constants and path helper functions used throughout the lecnotes CLI.

## Implementation

### Files Created
- `src/lecnotes/workdir.py` - The workdir layout module
- `tests/test_workdir.py` - Complete test suite for the module

### Module Contents

**Constants:**
- `MANIFEST = "manifest.json"`
- `SOURCE = "source.pdf"`
- `PAGES = "pages"`
- `NOTES = "NOTES.md"`
- `INSTRUCTIONS = "INSTRUCTIONS.md"`
- `OUT = "out"`
- `OUT_FIGURES = "out/figures"`

**Path helper functions:**
- `manifest_path(root: Path) -> Path`
- `source_path(root: Path) -> Path`
- `pages_dir(root: Path) -> Path`
- `notes_path(root: Path) -> Path`
- `instructions_path(root: Path) -> Path`
- `out_dir(root: Path) -> Path`
- `out_figures_dir(root: Path) -> Path`
- `page_png(root: Path, n: int) -> Path` - Zero-padded to 3 digits
- `page_txt(root: Path, n: int) -> Path` - Zero-padded to 3 digits
- `rel_png(n: int) -> str` - Manifest-relative POSIX string
- `rel_txt(n: int) -> str` - Manifest-relative POSIX string

**Workdir validation:**
- `is_workdir(root: Path) -> bool` - Checks if manifest.json exists
- `require_workdir(root: Path) -> None` - Raises `LecnotesError` with code "not_a_workdir" if manifest missing

**Manifest operations:**
- `save_manifest(root: Path, data: dict) -> None` - Saves JSON with 2-space indent and newline
- `load_manifest(root: Path) -> dict` - Loads manifest JSON

## TDD Process

### Step 1: RED - Test Fails
```bash
uv run pytest tests/test_workdir.py -v
```
**Result:** ImportError - module doesn't exist (expected)

### Step 2: GREEN - Tests Pass
After implementing `src/lecnotes/workdir.py`, all 7 new tests pass:

```bash
uv run pytest tests/test_workdir.py -v
```
**Result:** 7/7 tests PASSED

### Step 3: Full Suite
All 43 tests pass (36 existing + 7 new):

```bash
uv run pytest -v
```
**Result:** 43/43 tests PASSED

## Test Coverage

The test suite verifies:
1. Page path functions zero-pad to 3 digits
2. Relative path functions return POSIX strings with correct format
3. Named path functions return correct Path objects relative to root
4. `is_workdir()` detects presence of manifest.json
5. `require_workdir()` raises LecnotesError with correct code when manifest missing
6. Manifest save/load round-tripping preserves data
7. Manifest JSON is human-readable with proper indentation

## Deviation Notes
None. Implementation follows the brief exactly.

## Self-Review
- **Completeness:** All required functions and constants from brief implemented
- **Quality:** Clean, focused code; proper type hints; docstring explaining module purpose
- **Discipline:** No extra functionality; strictly YAGNI
- **Testing:** All assertions pass; TDD process followed exactly
- **Code standards:** Consistent with existing codebase; proper imports and error handling

## Commit
```
Commit: 7156123
Subject: Add workdir layout module
```

## Notes
- The module is properly positioned in the dependency graph (depends on errors.py, depended upon by other modules)
- All path helpers accept either Path or path-like objects via Path(root) conversion
- Manifest JSON formatting includes trailing newline for POSIX compliance
- Zero-padding in page file names uses Python's standard format string `{n:03d}`
