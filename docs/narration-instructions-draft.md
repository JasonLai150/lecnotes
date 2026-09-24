# Lecture narration — agent-facing instructions (draft)

Rendered into `INSTRUCTIONS.md` only when the workdir contains at least one
transcript. Tested against three real recordings; the wording below includes the
fixes both test runs asked for.

---

## Lecture narration

This deck was recorded. Alongside the slides you have one or more transcripts of
the lecture audio — `narration-1.md`, `narration-2.md` — each split into paragraphs
marked `[mm:ss]` from the start of that recording.

`NOTES.md` already exists. It was written from the slides alone, by someone who
never heard the lecture. Your job is to make it better using the recordings —
**by adding to it, never by taking away.**

Work in two steps: first write `NARRATION.md`, then revise `NOTES.md` from it.

### What narration is for, and what it is not for

The slides are authoritative for **definitions, equations, notation, constants,
terminology, and citations**. Where slide and speech disagree, the slide wins in
the notes, every time.

Use the narration for **emphasis** (what he spent time on, repeated, or called
important), **intuition, analogies and motivation**, **caveats and failure modes**
the slides state without qualification, and **corrections** he makes to his own
material.

The speech recognition is imperfect, especially on technical terms. Never copy its
wording.

### The recordings do not line up with the deck

Assume nothing. A recording may cover part of this deck, none of it, or a different
lecture entirely. He teaches out of order, doubles back, and skips slides.
Recordings overlap each other. Many slides are covered by no recording.

**Absence of narration is not evidence of unimportance.** This is the rule that has
failed most often in testing: a slide no recording reached must come out of this
process exactly as detailed as it went in.

Every recording contains stretches that are not course content — logistics,
deadlines, quiz mechanics, equipment failures, banter, and whatever was said after
teaching stopped while the recording kept running. Identify them and set them aside.

### Step 1 — write `NARRATION.md`

Read `NOTES.md` first, so you know which ideas the document is built around.
Organize `NARRATION.md` by **those ideas**, not by slide number and not by
recording. An idea is the right home for an explanation even when he gave it while
no slide was up.

Use exactly these labels, and omit any that has nothing in it:

```markdown
## Target networks and why plain online Q-learning diverges

**Slides:** 13-17 · recording 2, 22:10-31:40 (~9 min)
**Stressed:** ... (24:03)
**Intuition:** ... (25:40)
**Caveat:** ... (29:12)
**Softens:** slide 15 calls this "trivial"; he weakens it to "slightly easier"
  because a continuous action space makes the max an optimization. (26:15)
**Reframed:** he rewrites the estimator with the terms in a different order and
  says the two forms are the same thing. (27:02)
**Context:** this is what the field now calls ..., though the slide predates the
  name. (28:30)
**Correction:** he says slide 15 is wrong, because ... (30:02)
**Discrepancy:** he says 0.99; slide 13 says 0.999. He does not notice. (30:40)
**He asked:** ... — the answer he gave: ... (31:05)
```

Do not invent labels beyond these. The header carries the slide range, the
recording and the time span; each individual claim carries its own `[mm:ss]`, with
the recording number as well only when it comes from a different recording than the
header's. Where you are unsure of a claim, write `(uncertain)` directly after that
claim and say why — an unmarked guess is worse than an admitted one.

The labels that need definitions:

- **Correction** — he noticed his own material was wrong and said so.
- **Discrepancy** — he said something different without noticing. Recorded here;
  the slide's version is what reaches the notes.
- **Softens** — he weakens his slide's own wording without calling it wrong.
- **Reframed** — he restates the same result in different terms and asserts the two
  forms are equivalent.
- **Context** — what has happened to this field since the slides were made.
- **He asked** — a question he put to the room. Give the answer *he* gave, or write
  "left open" when he deliberately does not answer: a question that is itself the
  teaching point belongs here either way. You may paraphrase the *topic* of an
  audible student question so that his answer does not read as a non-sequitur, but
  never record what a student said, or how the room reacted — student audio is
  unreliable and frequently absent.

End the file with these three sections:

- `## Off the slides` — substantial teaching belonging to no slide: a board
  digression, an answer to a question, an argument he never wrote down. Expect this
  section to exist and to hold some of the best material in the lecture. If it is
  empty, you have probably forced content onto slides where it does not belong.
- `## Unresolved` — every garbled passage you could not settle from the slides, with
  its timestamp. Guessing at these is forbidden; listing them is required.
- `## Coverage` — for each recording, which slides it reaches and which time ranges
  were not course content, with what they were; then, once for the deck, which
  slides no recording reaches. A slide he passes over without teaching is not
  covered. If a recording is of a different lecture, say so in prose and use only
  the parts that bear on this deck.

**There is no length target.** Write what the material warrants and never pad. Do
not cut a real explanation to make the file shorter.

### Step 2 — revise `NOTES.md`

You may **add**: new sentences, new paragraphs, a new section, a new self-check
question, more depth on a thin passage. You may reorder sections so that what he
stressed comes earlier.

You may **not remove or replace** anything already in the document: not a fact, an
equation, a figure link, a citation, a definition, a code block, or a self-check
question. If the existing text and the narration disagree, the existing text stays
and you add the qualification beside it. In testing, the worst damage came from
narration-derived prose *displacing* correct slide-derived prose — an addition that
deletes is the failure this rule exists to prevent.

Two further rules, each from a real failure:

- **Every added claim traces to a specific passage.** If you need a connecting
  sentence that no one said, it is your own inference: either leave it out, or mark
  it `> **Beyond the slides:**` like any other addition of your own. A plausible
  bridge between two things he said, written in his voice, is a fabrication.
- **Keep his hedges.** Something offered loosely as intuition stays an intuition,
  with its qualification. A hedged analogy must never become a definition, and an
  approximate number he says aloud never replaces the slide's number.

Terminology he introduces that the slides lack — calling the acting policy the
*behaviour policy*, say — may be added, since it extends the slides rather than
contradicting them.

The narration must leave no visible trace: no timestamps, no "the instructor said",
no mention of recordings or of the lecture as an event. What he explained aloud
becomes ordinary prose in the document's own voice. `> **Beyond the slides:**` stays
reserved for what *you* add, not for what he said.

When you are done, re-read the sections covering slides no recording reached. They
should be untouched.
