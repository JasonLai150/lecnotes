### Task 5: Notion math passthrough, titles, README

**Files:**
- Modify: `src/lecnotes/export_notion.py`, `README.md`, `docs/BACKLOG.md`
- Test: `tests/test_export_notion.py`

**Interfaces:**
- Consumes: `mdparse.inline_text`
- Produces: nothing new

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_export_notion.py`:

```python
def test_math_passes_through_unwrap_unchanged():
    md = (
        "Policy $\\pi_\\theta(a_t \\mid s_t)$ acts\nhere.\n\n"
        "$$\n\\nabla_\\theta J(\\theta) =\n\\mathbb{E}[x]\n$$\n"
    )
    out = unwrap(md)
    assert "Policy $\\pi_\\theta(a_t \\mid s_t)$ acts here." in out
    assert "$$\n\\nabla_\\theta J(\\theta) =\n\\mathbb{E}[x]\n$$\n" in out


def test_title_keeps_math_source():
    # Math survives as its LaTeX source; the backslash is then an unsafe filename
    # character and becomes "-" like any other.
    stem, body = split_title("# The $\\pi$ policy\n\ntext\n", "lec1")
    assert stem == "The -pi policy"
    assert body == "text\n"


def test_math_is_byte_identical_in_the_zip(tmp_path):
    md = "# T\n\nInline $a_i * b_j$.\n\n$$\n\\sum_t r_t\n$$\n"
    dest = tmp_path / "t.zip"
    write_notion_zip(md, [], tmp_path, dest, "t")
    with zipfile.ZipFile(dest) as zf:
        text = zf.read("T.md").decode("utf-8")
    assert "Inline $a_i * b_j$." in text
    assert "$$\n\\sum_t r_t\n$$\n" in text
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_export_notion.py -v` → `test_title_keeps_math_source` FAILS (math dropped today, giving `The policy`).

- [ ] **Step 3: Implement**

In `src/lecnotes/export_notion.py`: import `inline_text` from `.mdparse` alongside `PARSER`, and in `split_title` replace the `PARSER.renderer.renderInlineAsText(...)` call with `inline_text(tokens[i + 1].children or [])`.

- [ ] **Step 4: README and backlog**

README: in the Export section, add one paragraph after the HTML bullet list:

```markdown
Equations are written as LaTeX (`$...$` inline, `$$` blocks), which VS Code,
GitHub and Obsidian preview directly. The HTML export renders them with a copy of
KaTeX embedded in the file (added only when the notes contain math, about 0.7 MB);
the Notion zip passes them through unchanged.
```

`docs/BACKLOG.md`: in "Not yet verified in real use", extend the Notion bullet with: "and how the importer treats `$...$` inline math and `$$` blocks". In "Features", replace the "Math rendering (in progress…)" entry with a one-line "Math rendering: done (LaTeX + KaTeX in HTML, passthrough to Notion)." — or remove it; keep the Observability entry unchanged.

- [ ] **Step 5: Run tests**

Run: `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 6: Commit**

Subject: "Keep math in Notion titles; document LaTeX math"
(stage `src/lecnotes/export_notion.py tests/test_export_notion.py README.md docs/BACKLOG.md`)

---

## After the plan (controller)

Regenerate CS 8803 DRL lectures 2 and 3 (`DRL lectures/draft-lec-2-…notes`, `draft-lec-3-…notes`): back up `NOTES.md` to `NOTES.before-latex.md`, `lecnotes prep <pdf> --force`, a fresh writing agent per lecture pointed only at `INSTRUCTIONS.md`, then `finish` and `export --to html` / `--to notion`. Report words, figures, LaTeX expressions, and agent feedback.

## Verification

- [ ] `uv run pytest -q` passes, no warnings
- [ ] A math-free export has no `<script>`; a math export renders in a browser with KaTeX
- [ ] The wheel contains the 20 KaTeX fonts

---

### Added by the controller: Task 2 review fix (fold into this task's commit)

Task 2's review found that the Equations example in `src/lecnotes/templates/instructions.md` is indented 4 spaces (to mark it as an example), and an agent copying that indentation into NOTES.md produces an indented code block — the `$$` equation then renders as raw LaTeX, silently.

- In the Equations section, change the sentence starting "Put each `$$` on its own line" to:
  `Put each $$ on its own line, flush left with no indentation (the indentation above only marks the example), with a blank line before and after the block.`
  Keep the `$$` inside backticks exactly as the existing sentence does: `` Put each `$$` on its own line, flush left with no indentation (the indentation above only marks the example), with a blank line before and after the block. ``
- Add to `tests/test_instructions.py`:

```python
def test_display_math_must_be_flush_left():
    out = rendered()
    assert "flush left" in out
```

- Add to `tests/test_mdparse.py` (documents why the rule exists):

```python
def test_indented_display_math_is_a_code_block_not_math():
    tokens = PARSER.parse("Text.\n\n    $$\n    x^2\n    $$\n")
    assert not any(t.type == "math_block" for t in tokens)
    assert any(t.type == "code_block" for t in tokens)
```

Stage these files in the same commit as the rest of Task 5.
