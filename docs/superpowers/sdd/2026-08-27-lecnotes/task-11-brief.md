### Task 11: The `finish` command

**Files:**
- Modify: `src/lecnotes/commands.py`
- Create: `tests/test_finish.py`

**Interfaces:**
- Consumes: `commands.NOTES_STUB`, `figures.find_refs`, `figures.crop_render`, `workdir.*`
- Produces: `finish(root: Path) -> dict` returning `{"ok": True, "workdir", "deck", "output", "figures_resolved"}`

- [ ] **Step 1: Write the failing test**

Create `tests/test_finish.py`:

```python
import pytest

from lecnotes import workdir
from lecnotes.commands import finish, prep
from lecnotes.errors import LecnotesError


@pytest.fixture
def prepared(synth, tmp_path):
    """A prepped 5-slide workdir, ready for notes to be written into."""
    pdf = synth(
        tmp_path / "lec1.pdf",
        [{"text": f"Slide {i}", "small_box": (100, 100, 300, 220)} for i in range(1, 6)],
    )
    prep(pdf)
    return tmp_path / "lec1.notes"


def write_notes(root, body):
    workdir.notes_path(root).write_text(body, encoding="utf-8")


def test_assembles_the_output_document(prepared):
    write_notes(prepared, "# B+ Trees\n\nFanout buys shallowness.\n")
    result = finish(prepared)
    out = workdir.out_dir(prepared) / "lec1.md"
    assert out.is_file()
    assert "Fanout buys shallowness." in out.read_text()
    assert result["output"] == str(out)
    assert result["ok"] is True


def test_resolves_and_crops_referenced_figures(prepared):
    write_notes(prepared, "# T\n\n![the node](figures/slide-003.png)\n")
    result = finish(prepared)
    assert result["figures_resolved"] == 1
    assert (workdir.out_figures_dir(prepared) / "slide-003.png").is_file()


def test_only_referenced_slides_are_copied(prepared):
    write_notes(prepared, "![a](figures/slide-002.png)\n![b](figures/slide-004.png)\n")
    finish(prepared)
    names = sorted(p.name for p in workdir.out_figures_dir(prepared).glob("*.png"))
    assert names == ["slide-002.png", "slide-004.png"]


def test_notes_with_no_figures_still_builds(prepared):
    write_notes(prepared, "# All prose\n")
    assert finish(prepared)["figures_resolved"] == 0


def test_out_of_range_reference_is_named(prepared):
    write_notes(prepared, "![x](figures/slide-091.png)\n")
    with pytest.raises(LecnotesError) as exc:
        finish(prepared)
    assert exc.value.code == "figure_out_of_range"
    assert exc.value.exit_code == 1
    assert exc.value.detail["bad_refs"] == [{"slide": 91, "max": 5}]


def test_every_bad_reference_is_reported_not_just_the_first(prepared):
    write_notes(prepared, "![x](figures/slide-091.png)\n![y](figures/slide-007.png)\n")
    with pytest.raises(LecnotesError) as exc:
        finish(prepared)
    assert exc.value.detail["bad_refs"] == [{"slide": 7, "max": 5}, {"slide": 91, "max": 5}]


def test_nothing_is_written_when_validation_fails(prepared):
    write_notes(prepared, "![x](figures/slide-091.png)\n")
    with pytest.raises(LecnotesError):
        finish(prepared)
    assert not workdir.out_dir(prepared).exists()


def test_unwritten_notes_are_refused(prepared):
    with pytest.raises(LecnotesError) as exc:
        finish(prepared)
    assert exc.value.code == "notes_empty"
    assert exc.value.exit_code == 1


def test_non_workdir_is_refused(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        finish(tmp_path)
    assert exc.value.code == "not_a_workdir"


def test_rebuild_clears_stale_figures(prepared):
    write_notes(prepared, "![a](figures/slide-002.png)\n")
    finish(prepared)
    write_notes(prepared, "![b](figures/slide-004.png)\n")
    finish(prepared)
    names = sorted(p.name for p in workdir.out_figures_dir(prepared).glob("*.png"))
    assert names == ["slide-004.png"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_finish.py -v`
Expected: FAIL with `ImportError: cannot import name 'finish'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/lecnotes/commands.py`:

```python
def finish(root: Path) -> dict:
    root = Path(root)
    workdir.require_workdir(root)

    manifest = workdir.load_manifest(root)
    notes = workdir.notes_path(root)
    body = notes.read_text(encoding="utf-8") if notes.is_file() else ""

    if body.strip() == NOTES_STUB.strip() or not body.strip():
        raise LecnotesError(
            "notes_empty",
            f"{notes} has not been written yet; see {workdir.INSTRUCTIONS}",
            path=str(notes),
        )

    slides = manifest["slides"]
    refs = find_refs(body)

    # Validate every reference before writing anything, so a bad link leaves no
    # half-built output behind.
    bad = [{"slide": n, "max": slides} for n in refs if not 1 <= n <= slides]
    if bad:
        raise LecnotesError(
            "figure_out_of_range",
            "NOTES.md references slides that are not in this deck: "
            + ", ".join(str(b["slide"]) for b in bad)
            + f" (deck has {slides})",
            bad_refs=bad,
        )

    figures_dir = workdir.out_figures_dir(root)
    if figures_dir.exists():
        shutil.rmtree(figures_dir)  # a rebuild must not leave last run's figures
    figures_dir.mkdir(parents=True, exist_ok=True)

    source = workdir.source_path(root)
    for n in refs:
        crop_render(source, n, figures_dir / f"slide-{n:03d}.png")

    out = workdir.out_dir(root) / f"{manifest['deck']}.md"
    out.write_text(body, encoding="utf-8")

    return {
        "ok": True,
        "workdir": str(root),
        "deck": manifest["deck"],
        "output": str(out),
        "figures_resolved": len(refs),
    }
```

Extend the existing import of `.figures` at the top of the file to
`from .figures import TARGET_LONG_EDGE, crop_render, find_refs`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_finish.py -v`
Expected: PASS, 10 tests

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/commands.py tests/test_finish.py
git commit -m "Add the finish command"
```

---

