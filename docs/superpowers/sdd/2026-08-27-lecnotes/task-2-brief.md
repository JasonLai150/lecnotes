### Task 2: Deck-name slugging

**Files:**
- Create: `src/lecnotes/naming.py`
- Create: `tests/test_naming.py`

**Interfaces:**
- Consumes: nothing
- Produces: `slugify(name: str) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_naming.py`:

```python
import pytest

from lecnotes.naming import slugify


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("lec1-history", "lec1-history"),
        ("lec8-txn,cc", "lec8-txn-cc"),            # commas appear in real deck names
        ("lec19-gfs,mr", "lec19-gfs-mr"),
        ("Final Review", "final-review"),
        ("CS4440__Lecture  3", "cs4440-lecture-3"),
        ("--leading-and-trailing--", "leading-and-trailing"),
        ("weird!!!name", "weird-name"),
    ],
)
def test_slugify(raw, expected):
    assert slugify(raw) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_naming.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.naming'`

- [ ] **Step 3: Write minimal implementation**

Create `src/lecnotes/naming.py`:

```python
"""Deck-name derivation.

The slug names the workdir and the output file, so it has to survive the
punctuation real lecture filenames carry (`lec8-txn,cc.pdf`).
"""

import re


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_naming.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/naming.py tests/test_naming.py
git commit -m "Add deck-name slugging"
```

---

