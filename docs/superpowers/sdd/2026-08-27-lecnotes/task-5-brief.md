### Task 5: Figure reference scanning

**Files:**
- Modify: `src/lecnotes/figures.py`
- Create: `tests/test_figures_refs.py`

**Interfaces:**
- Consumes: `src/lecnotes/figures.py` from Task 4
- Produces: `find_refs(markdown: str) -> list[int]` — sorted, de-duplicated 1-indexed slide numbers referenced by `![alt](figures/slide-NNN.png)`. Also exports the compiled `REF_RE`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_figures_refs.py`:

```python
from lecnotes.figures import find_refs


def test_finds_a_single_ref():
    assert find_refs("![a tree](figures/slide-008.png)") == [8]


def test_finds_refs_with_empty_alt_text():
    assert find_refs("![](figures/slide-012.png)") == [12]


def test_sorts_and_dedupes():
    md = """
    ![x](figures/slide-012.png)
    ![y](figures/slide-003.png)
    ![z](figures/slide-012.png)
    """
    assert find_refs(md) == [3, 12]


def test_ignores_other_images():
    md = "![logo](assets/logo.png) ![ok](figures/slide-005.png) ![n](figures/slide-5.png)"
    assert find_refs(md) == [5]


def test_ignores_prose_that_merely_mentions_the_path():
    assert find_refs("link figures/slide-008.png like this") == []


def test_empty_document_has_no_refs():
    assert find_refs("") == []


def test_alt_text_with_punctuation_still_matches():
    md = "![B+ tree (fanout 133), annotated](figures/slide-014.png)"
    assert find_refs(md) == [14]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_figures_refs.py -v`
Expected: FAIL with `ImportError: cannot import name 'find_refs'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/lecnotes/figures.py`:

```python
import re

# Exactly the form INSTRUCTIONS.md tells the agent to write. A workdir holds one
# deck, so there is no deck path segment.
REF_RE = re.compile(r"!\[([^\]]*)\]\(figures/slide-(\d{3})\.png\)")


def find_refs(markdown: str) -> list[int]:
    """Sorted, de-duplicated slide numbers referenced as figures."""
    return sorted({int(n) for _, n in REF_RE.findall(markdown)})
```

Move the `import re` up with the other imports at the top of the file rather than leaving it mid-module.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_figures_refs.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/figures.py tests/test_figures_refs.py
git commit -m "Add figure reference scanning"
```

---

