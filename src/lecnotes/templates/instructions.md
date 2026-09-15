# Write the notes for `{{deck}}`

You are writing a teaching document from a lecture deck. Everything you need is
in this directory.

## Source material

The deck is `source.pdf` (originally `{{source_name}}`), **{{slides}} slides**. For each
slide there are two files:

- `pages/slide-001.png` — the rendered slide, exactly as the lecture shows it.
- `pages/slide-001.txt` — the text extracted from that slide, for exact wording
  and symbols.

**View every slide image, including slides that look like plain text.** The
`.txt` files are incomplete: equations, diagram labels, and sometimes a slide's
entire content exist only in the image. A `.txt` file holding only a title, or
nothing at all, usually means the substance is in the image. `manifest.json` lists
each slide's `chars` count.

## What to write

Write the document to **`NOTES.md`** in this directory, replacing the stub.

Write it the way a good study guide reads: organized by idea rather than by slide
order, compressed, leading with the point. Explain why each mechanism exists, what
problem it solves, and when it applies.

Skip course logistics, title/agenda/recap/attribution slides, and worked examples
that walk through a procedure by hand.

Use `#` for the title, `##` and `###` for sections. Tables are welcome. End with a
`## Self-check` section of conceptual questions.

### Equations

Write math as LaTeX. Use `$...$` for math inside a sentence, and a display block
for an equation that stands on its own:

    The policy $\pi_\theta(a_t \mid s_t)$ maps states to action probabilities.

    $$
    \nabla_\theta J(\theta) = \mathbb{E}_{\tau \sim p_\theta}\left[\sum_t \nabla_\theta \log \pi_\theta(a_t \mid s_t)\, \hat{A}_t\right]
    $$

Put each `$$` on its own line, flush left with no indentation (the indentation
above only marks the example) — except inside a list item, where the `$$` lines
are indented to line up with the item's text — with a blank line before and after
the block. No space just inside the dollar signs (`$x$`, not `$ x $`). Write a
literal dollar sign as `\$`. Never use code spans or code blocks for math — keep
those for code, identifiers, commands, and file names. Keep math out of the `#`
title.

Type every equation, including ones the slide shows only as an image, and define
the variables it uses. Do not link a slide as a figure just to show an equation.

Inside a table cell, write `\mid`, `\vert`, or `\lVert … \rVert` instead of `|` or
`\|` — a bare pipe splits the cell.

### Going beyond the slides

You may add explanation the slides do not contain when it helps a reader
understand: answering a question a slide poses, deriving a result a slide only
states, or supplying a standard fact the lecture assumes. Keep additions correct
and consistent with the slides, and mark each one so a reader can tell it apart
from the lecture's own content:

    > **Beyond the slides:** the explanation goes here.

### Code

When the slides present an algorithm or procedure, you may write it as a fenced
code block. Keep it faithful to the slides — the same steps, in the same order,
with the same names — and do not invent detail the lecture does not give. Unless
the slides show real code in a specific language, call it pseudocode in the
sentence before the block and fence it as `text`.

## Including a figure

Link a slide as a figure when it shows something text cannot carry: a diagram, a
plot, an architecture, a visual example. Prefer showing such a figure over
describing it.

    ![a short caption describing what the figure shows](figures/slide-NNN.png)

The path is `figures/`, not `pages/`, with no `./` prefix, and the slide number is
zero-padded to three digits. If the caption needs square brackets, keep them
balanced. Any other form of slide image link is rejected.

Only link slides you actually looked at. The next step crops each linked slide to
its content and copies it into place; linking a slide that does not exist is an
error.

## When you are done

Run this from inside this directory:

    lecnotes finish .

That validates your figure links, crops and copies the figures, and assembles
`out/{{deck}}.md`.
