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
