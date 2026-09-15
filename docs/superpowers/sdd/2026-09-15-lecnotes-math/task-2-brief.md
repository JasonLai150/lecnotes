### Task 2: Instructions tell agents to write LaTeX

**Files:**
- Modify: `src/lecnotes/instructions.py`, `src/lecnotes/templates/instructions.md`
- Test: `tests/test_instructions.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `render_instructions(deck, slides, source_name) -> str` (signature unchanged)

- [ ] **Step 1: Update the tests first**

In `tests/test_instructions.py`, replace `test_no_unreplaced_placeholders` with:

```python
def test_no_unreplaced_placeholders():
    out = rendered()
    assert "{{" not in out and "}}" not in out


def test_equations_are_latex():
    out = rendered()
    assert "$\\pi_\\theta(a_t \\mid s_t)$" in out
    assert "\n    $$\n" in out
    assert "\\$" in out  # how to write a literal dollar
    assert "code spans" in out


def test_no_plain_text_equation_wording():
    assert "Type every equation as plain text" not in rendered()


def test_values_containing_braces_or_dollars_are_inserted_verbatim():
    out = rendered(deck="lec-{x}$", source_name="$deck{{slides}}.pdf")
    assert "lec-{x}$" in out
    assert "$deck{{slides}}.pdf" in out
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_instructions.py -v` → the new tests FAIL.

- [ ] **Step 3: Implement the loader**

Replace `src/lecnotes/instructions.py` with:

```python
"""Fill the agent-facing contract template.

Placeholders are {{name}}. The template teaches LaTeX, so it is full of dollar
signs; string.Template's $-placeholders would collide with them.
"""

import re
from importlib.resources import files

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def render_instructions(deck: str, slides: int, source_name: str) -> str:
    raw = files("lecnotes.templates").joinpath("instructions.md").read_text(encoding="utf-8")
    values = {"deck": deck, "slides": str(slides), "source_name": source_name}
    # One pass, so a value that itself contains "{{...}}" is never re-expanded.
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], raw)
```

- [ ] **Step 4: Update the template**

In `src/lecnotes/templates/instructions.md`: replace every `$deck` with `{{deck}}`, `$slides` with `{{slides}}`, `$source_name` with `{{source_name}}` (including the `out/$deck.md` at the end). Then replace the whole `### Equations` section (heading through the paragraph before `### Going beyond the slides`) with exactly:

```markdown
### Equations

Write math as LaTeX. Use `$...$` for math inside a sentence, and a display block
for an equation that stands on its own:

    The policy $\pi_\theta(a_t \mid s_t)$ maps states to action probabilities.

    $$
    \nabla_\theta J(\theta) = \mathbb{E}_{\tau \sim p_\theta}\left[\sum_t \nabla_\theta \log \pi_\theta(a_t \mid s_t)\, \hat{A}_t\right]
    $$

Put each `$$` on its own line, with a blank line before and after the block. No
space just inside the dollar signs (`$x$`, not `$ x $`). Write a literal dollar
sign as `\$`. Never use code spans or code blocks for math — keep those for code,
identifiers, commands, and file names.

Type every equation, including ones the slide shows only as an image, and define
the variables it uses. Do not link a slide as a figure just to show an equation.
```

Leave the rest of the template unchanged.

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_instructions.py tests/test_prep.py -v` → PASS. Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 6: Commit**

Subject: "Tell agents to write equations as LaTeX"

---

