### Task 1: Project scaffolding and the error type

**Files:**
- Create: `pyproject.toml`
- Create: `src/lecnotes/__init__.py`
- Create: `src/lecnotes/errors.py`
- Create: `tests/test_errors.py`

**Interfaces:**
- Consumes: nothing
- Produces: `LecnotesError(code: str, message: str, **detail)` with attributes `.code: str`, `.message: str`, `.detail: dict`, and property `.exit_code: int` (2 for `missing_converter` and `conversion_failed`, else 1). Method `.to_dict() -> dict` returning `{"ok": False, "error": code, **detail}`.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "lecnotes"
version = "0.1.0"
description = "Turn a lecture deck into a workdir any coding agent can write notes from"
requires-python = ">=3.11"
dependencies = ["pymupdf>=1.24"]

[project.scripts]
lecnotes = "lecnotes.cli:main"

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/lecnotes"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `src/lecnotes/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Run `uv sync` to build the environment**

Run: `uv sync`
Expected: creates `.venv`, installs pymupdf and pytest. Confirm with `uv run python -c "import pymupdf; print(pymupdf.__doc__)"`.

- [ ] **Step 4: Write the failing test**

Create `tests/test_errors.py`:

```python
import pytest

from lecnotes.errors import LecnotesError


def test_carries_code_message_and_detail():
    err = LecnotesError("notes_empty", "NOTES.md is still the stub", path="a/NOTES.md")
    assert err.code == "notes_empty"
    assert err.message == "NOTES.md is still the stub"
    assert err.detail == {"path": "a/NOTES.md"}


def test_str_is_the_message():
    assert str(LecnotesError("notes_empty", "boom")) == "boom"


@pytest.mark.parametrize(
    "code,expected",
    [
        ("missing_converter", 2),
        ("conversion_failed", 2),
        ("unsupported_format", 1),
        ("workdir_exists", 1),
        ("not_a_workdir", 1),
        ("notes_empty", 1),
        ("figure_out_of_range", 1),
    ],
)
def test_exit_code_per_error_code(code, expected):
    assert LecnotesError(code, "msg").exit_code == expected


def test_to_dict_merges_detail():
    err = LecnotesError("figure_out_of_range", "bad ref", bad_refs=[{"slide": 91, "max": 47}])
    assert err.to_dict() == {
        "ok": False,
        "error": "figure_out_of_range",
        "bad_refs": [{"slide": 91, "max": 47}],
    }
```

- [ ] **Step 5: Run test to verify it fails**

Run: `uv run pytest tests/test_errors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.errors'`

- [ ] **Step 6: Write minimal implementation**

Create `src/lecnotes/errors.py`:

```python
"""The single exception type every failure travels through.

cli.py catches this in one place and renders it as human text or JSON, which is
what keeps the two output modes from drifting apart.
"""

# Missing or broken external tooling is the user's environment, not their input,
# so it gets its own exit code.
_DEPENDENCY_CODES = {"missing_converter", "conversion_failed"}


class LecnotesError(Exception):
    def __init__(self, code: str, message: str, **detail):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail

    @property
    def exit_code(self) -> int:
        return 2 if self.code in _DEPENDENCY_CODES else 1

    def to_dict(self) -> dict:
        return {"ok": False, "error": self.code, **self.detail}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_errors.py -v`
Expected: PASS, 10 tests

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock src/lecnotes/__init__.py src/lecnotes/errors.py tests/test_errors.py
git commit -m "Add project scaffolding and the LecnotesError type"
```

---

