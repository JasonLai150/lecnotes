### Task 9: The instructions template

**Files:**
- Create: `src/lecnotes/templates/instructions.md`
- Create: `src/lecnotes/instructions.py`
- Create: `tests/test_instructions.py`
- Modify: `pyproject.toml` (include the template in the wheel)

**Interfaces:**
- Consumes: nothing
- Produces: `render_instructions(deck: str, slides: int, figures: int, source_name: str, workdir_name: str) -> str`

**Note on scope:** the *mechanics* of this text are specified; its *editorial* half (audience, depth, voice) ships as the generic default below and gets tuned later by editing this one file. Do not add configuration for it now.

- [ ] **Step 1: Write the failing test**

Create `tests/test_instructions.py`:

```python
from lecnotes.instructions import render_instructions


def rendered(**kw):
    args = dict(
        deck="lec1", slides=47, figures=29,
        source_name="lec1.pdf", workdir_name="lec1.notes",
    )
    args.update(kw)
    return render_instructions(**args)


def test_states_the_deck_and_counts():
    out = rendered()
    assert "lec1" in out
    assert "47" in out
    assert "29" in out


def test_shows_the_exact_figure_link_syntax():
    assert "![" in rendered() and "](figures/slide-NNN.png)" in rendered()


def test_names_the_file_to_write():
    assert "NOTES.md" in rendered()


def test_names_the_command_to_run_when_done():
    assert "lecnotes finish lec1.notes" in rendered()


def test_points_at_both_the_png_and_the_txt():
    out = rendered()
    assert "pages/slide-001.png" in out
    assert "pages/slide-001.txt" in out


def test_no_unreplaced_placeholders():
    assert "{" not in rendered().replace("{{", "").replace("}}", "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_instructions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.instructions'`

- [ ] **Step 3: Write the template**

Create `src/lecnotes/templates/instructions.md`:

```markdown
# Write the notes for `$deck`

You are writing a teaching document from a lecture deck. Everything you need is
in this directory.

## Source material

`$source_name` — **$slides slides**, $figures of which carry figures.

For each slide N there are two files:

- `pages/slide-001.png` — the rendered slide. **Diagrams exist only here.**
- `pages/slide-001.txt` — that slide's exact text, so wording and symbols stay
  lossless.

Read both for every slide. `manifest.json` lists every page with a `figure` flag
telling you which ones repay a close look; it is a hint, not a filter.

## What to write

Write the document to **`NOTES.md`** in this directory, replacing the stub.

Write it the way a good study guide reads: organized by idea rather than by slide
order, compressed, leading with the point. Explain why each mechanism exists, what
problem it solves, and when it applies. Prefer showing a diagram over describing
one.

Skip course logistics, title/agenda/recap/attribution slides, and worked examples
that walk through a procedure by hand.

Keep formulas as plain text with their variables defined — `O(N log N)`,
`T(R)/V(R,a)`.

Use `#` for the title, `##` and `###` for sections. Tables are welcome. End with a
`## Self-check` section of conceptual questions.

## Including a figure

Link it exactly like this, with the slide number zero-padded to three digits:

    ![a short caption describing what the figure shows](figures/slide-NNN.png)

Only link slides you actually looked at. The next step crops each linked slide to
its content and copies it into place; linking a slide that does not exist is an
error.

## When you are done

    lecnotes finish $workdir_name

That validates your figure links, crops and copies the figures, and assembles
`out/$deck.md`.
```

- [ ] **Step 4: Write the loader**

Create `src/lecnotes/instructions.py`:

```python
"""Fill the agent-facing contract template.

string.Template is deliberate: the template is full of Markdown braces and
backticks, and $-substitution leaves all of them alone.
"""

from importlib.resources import files
from string import Template


def render_instructions(
    deck: str, slides: int, figures: int, source_name: str, workdir_name: str
) -> str:
    raw = files("lecnotes.templates").joinpath("instructions.md").read_text(encoding="utf-8")
    return Template(raw).substitute(
        deck=deck,
        slides=slides,
        figures=figures,
        source_name=source_name,
        workdir_name=workdir_name,
    )
```

- [ ] **Step 5: Confirm the template ships with the package**

Hatchling's `packages = ["src/lecnotes"]` already includes every file under the
package directory, `.md` included — no `force-include` is needed, and adding one
would collide with the path hatchling picks up anyway. Just verify the resource
actually loads:

Run: `uv run python -c "from importlib.resources import files; print(len(files('lecnotes.templates').joinpath('instructions.md').read_text()))"`
Expected: a non-zero character count.

If it raises, the cause is a missing `src/lecnotes/templates/__init__.py`. Add an
empty one and re-run.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_instructions.py -v`
Expected: PASS, 6 tests

- [ ] **Step 7: Commit**

```bash
git add src/lecnotes/templates/ src/lecnotes/instructions.py tests/test_instructions.py
git commit -m "Add the agent-facing instructions template"
```

---

