### Task 6: Workdir layout

**Files:**
- Create: `src/lecnotes/workdir.py`
- Create: `tests/test_workdir.py`

**Interfaces:**
- Consumes: `lecnotes.errors.LecnotesError`
- Produces, all taking the workdir root as a `Path`:
  - Constants `MANIFEST = "manifest.json"`, `SOURCE = "source.pdf"`, `PAGES = "pages"`, `NOTES = "NOTES.md"`, `INSTRUCTIONS = "INSTRUCTIONS.md"`, `OUT = "out"`, `OUT_FIGURES = "out/figures"`
  - `manifest_path(root)`, `source_path(root)`, `pages_dir(root)`, `notes_path(root)`, `instructions_path(root)`, `out_dir(root)`, `out_figures_dir(root)`
  - `page_png(root, n) -> Path` and `page_txt(root, n) -> Path` (3-digit zero padding)
  - `rel_png(n) -> str` and `rel_txt(n) -> str` — manifest-relative POSIX strings
  - `is_workdir(root) -> bool`
  - `require_workdir(root) -> None` — raises `LecnotesError("not_a_workdir", ...)`
  - `save_manifest(root, data) -> None`, `load_manifest(root) -> dict`

- [ ] **Step 1: Write the failing test**

Create `tests/test_workdir.py`:

```python
import pytest

from lecnotes import workdir
from lecnotes.errors import LecnotesError


def test_page_paths_zero_pad_to_three_digits(tmp_path):
    assert workdir.page_png(tmp_path, 8).name == "slide-008.png"
    assert workdir.page_txt(tmp_path, 8).name == "slide-008.txt"
    assert workdir.page_png(tmp_path, 147).name == "slide-147.png"


def test_relative_page_paths_are_posix(tmp_path):
    assert workdir.rel_png(8) == "pages/slide-008.png"
    assert workdir.rel_txt(8) == "pages/slide-008.txt"


def test_named_paths_hang_off_the_root(tmp_path):
    assert workdir.manifest_path(tmp_path) == tmp_path / "manifest.json"
    assert workdir.source_path(tmp_path) == tmp_path / "source.pdf"
    assert workdir.notes_path(tmp_path) == tmp_path / "NOTES.md"
    assert workdir.instructions_path(tmp_path) == tmp_path / "INSTRUCTIONS.md"
    assert workdir.out_figures_dir(tmp_path) == tmp_path / "out" / "figures"


def test_is_workdir_requires_a_manifest(tmp_path):
    assert not workdir.is_workdir(tmp_path)
    workdir.save_manifest(tmp_path, {"deck": "d"})
    assert workdir.is_workdir(tmp_path)


def test_require_workdir_raises_when_absent(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        workdir.require_workdir(tmp_path)
    assert exc.value.code == "not_a_workdir"
    assert exc.value.exit_code == 1


def test_manifest_roundtrips(tmp_path):
    data = {"deck": "lec1", "slides": 47, "pages": [{"n": 1, "chars": 31, "figure": False}]}
    workdir.save_manifest(tmp_path, data)
    assert workdir.load_manifest(tmp_path) == data


def test_manifest_is_readable_json(tmp_path):
    workdir.save_manifest(tmp_path, {"deck": "lec1"})
    assert '"deck": "lec1"' in workdir.manifest_path(tmp_path).read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_workdir.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.workdir'`

- [ ] **Step 3: Write minimal implementation**

Create `src/lecnotes/workdir.py`:

```python
"""The one module that knows the workdir layout.

Both commands go through here, so path literals do not scatter across the
codebase.
"""

import json
from pathlib import Path

from .errors import LecnotesError

MANIFEST = "manifest.json"
SOURCE = "source.pdf"
PAGES = "pages"
NOTES = "NOTES.md"
INSTRUCTIONS = "INSTRUCTIONS.md"
OUT = "out"
OUT_FIGURES = "out/figures"


def manifest_path(root: Path) -> Path:
    return Path(root) / MANIFEST


def source_path(root: Path) -> Path:
    return Path(root) / SOURCE


def pages_dir(root: Path) -> Path:
    return Path(root) / PAGES


def notes_path(root: Path) -> Path:
    return Path(root) / NOTES


def instructions_path(root: Path) -> Path:
    return Path(root) / INSTRUCTIONS


def out_dir(root: Path) -> Path:
    return Path(root) / OUT


def out_figures_dir(root: Path) -> Path:
    return Path(root) / OUT / "figures"


def page_png(root: Path, n: int) -> Path:
    return pages_dir(root) / f"slide-{n:03d}.png"


def page_txt(root: Path, n: int) -> Path:
    return pages_dir(root) / f"slide-{n:03d}.txt"


def rel_png(n: int) -> str:
    return f"{PAGES}/slide-{n:03d}.png"


def rel_txt(n: int) -> str:
    return f"{PAGES}/slide-{n:03d}.txt"


def is_workdir(root: Path) -> bool:
    return manifest_path(root).is_file()


def require_workdir(root: Path) -> None:
    if not is_workdir(root):
        raise LecnotesError(
            "not_a_workdir",
            f"{root} is not a lecnotes workdir (no {MANIFEST})",
            path=str(root),
        )


def save_manifest(root: Path, data: dict) -> None:
    Path(root).mkdir(parents=True, exist_ok=True)
    manifest_path(root).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_manifest(root: Path) -> dict:
    return json.loads(manifest_path(root).read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_workdir.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/workdir.py tests/test_workdir.py
git commit -m "Add workdir layout module"
```

---

