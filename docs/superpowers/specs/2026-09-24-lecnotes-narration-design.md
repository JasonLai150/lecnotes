# lecnotes narration — design

**Date:** 2026-09-24
**Status:** approved design
**Extends:** `2026-08-27-lecnotes-design.md`, `2026-09-15-lecnotes-export-design.md`,
`2026-09-15-lecnotes-math-design.md` (with their amendments)

## Problem

Notes written from a deck alone miss what was taught. The slides carry the claims;
the lecture carries the reasons, the caveats, and the emphasis. A measured example
from CS 8803 DRL lecture 2: the notes ask, as a self-check question, "why can the
greedy policy stop changing long before the values do?" and never answer it
anywhere — because the slide that answered it was deleted and the answer survives
only in the recording.

## Evidence

This design is built on an experiment against real material, not on judgement
alone. Three recordings (73, 69 and 46 minutes) and four decks were used. The
findings that shaped the design:

- **Tool-side alignment is not viable.** IDF-weighted matching of transcript
  paragraphs to slides produced a confident-looking best match for 98% of
  paragraphs, but 43% of consecutive matches moved backwards through the deck, and
  the opening logistics matched a mid-deck slide above threshold. Agent-side
  mapping, by contrast, placed 11 of 12 probe points correctly.
- **Recordings and decks do not correspond.** A 73-minute recording covered slides
  9–53 of a 98-slide deck. Another was half a different lecture. Across three
  recordings, between 46% and 76% of each deck was reached by no narration at all.
  Decks also duplicate each other: 17 slides of the actor-critic deck are verbatim
  twins of policy-gradient slides.
- **The best material often has no slide.** ~13 minutes of one lecture — including
  the advantage function, which appears in *no* slide text in either deck — was
  taught with nothing on screen.
- **Fabrication is the real risk, and it displaces.** In a sampled audit, 10 of 13
  narration-derived claims were supported, 2 embellished, 1 unsupported — and the
  unsupported one pushed out a correct slide-derived explanation.
- **A single agent doing both jobs damages the document.** Writing notes from
  slides and narration together silently lost 11 display equations, all 4 code
  blocks, 2 figures and 3 self-check questions relative to the slides-only version,
  and hollowed the un-narrated half of the deck: self-check coverage of that range
  fell from 43% to 18% at unchanged word count.
- **An additive enrichment pass fixes this.** Two runs over existing notes added
  38% and 64% more words, 10 and 9 self-check questions, and removed nothing:
  211 of 211 and 264 of 266 draft sentences survived, with every figure, equation
  and code block intact.

## Decision

Narration is a third stage, not a second input to the first.

1. `prep --transcript` normalizes recordings into the workdir.
2. The notes are written from the slides alone, exactly as today.
3. An **enrichment pass** rewrites those notes using the narration, and may only
   add.

The slides remain authoritative for definitions, equations, notation, constants,
terminology and citations. Narration supplies emphasis, intuition, motivation,
caveats and corrections. Where the two disagree, the slide governs the notes and
the disagreement is recorded.

## Input: `prep --transcript`

`lecnotes prep deck.pdf --transcript FILE [--transcript FILE ...]`

Repeatable, because one deck spans several sessions and one session spans several
decks. Format is detected from content, not extension: word-level JSON (Kaltura
shape: `w`, `s`, `e`, optional confidence `a`), SRT, WebVTT, or plain text.

**Time scale is discovered, not assumed.** The Kaltura files here use 10 ms ticks;
read as milliseconds the lecture appears to run 7 minutes at 1,400 words per
minute. `prep` picks the scale whose implied speaking rate is plausible
(60–260 wpm) and fails with a specific error if none is.

Each transcript is normalized to `narration-<N>.md` in the workdir:

```
# Lecture narration — recording 1 of 2
73 minutes, 10,397 words. Times are mm:ss into the recording.

[03:49] Okay, cool. Carrying on from where we left off, we were talking about …
```

Every word is kept verbatim: no filler stripping, no attempt to repair ASR errors.
The only additions are paragraph breaks at the longest pauses (capped near 170
words) and an `[mm:ss]` marker per paragraph. Plain-text input with no timings gets
no markers and a header saying so.

The raw file is not copied into the workdir. `manifest.json` gains a `transcripts`
array recording each source name, format, minutes, word count and whether it is
timed. Absent when no transcript was given.

## Stage 2: `NARRATION.md`

Written by the agent before any revision, organized by **the ideas the notes are
built around** — not by slide, and not by recording. An idea is the right home for
an explanation even when it was given with nothing on screen, and the notes are
already organized by idea rather than slide order.

Labels are a closed set: `Stressed`, `Intuition`, `Caveat`, `Softens`, `Reframed`,
`Context`, `Correction`, `Discrepancy`, `He asked`. The last four are the ones
testing showed need definitions:

- **Correction** — he noticed his own material was wrong and said so.
- **Discrepancy** — he said something different without noticing. Recorded; the
  slide still governs the notes.
- **Softens** — he weakens his own slide's wording without calling it wrong
  ("completely trivial" → "slightly easier").
- **Reframed** — he restates the same result in different terms and asserts the
  forms are equivalent.
- **Context** — what has happened to the field since the slides were made.
- **He asked** — a question he put to the room, with the answer *he* gave, or
  marked as deliberately left open. The topic of an audible student question may be
  paraphrased minimally so his answer is not a non-sequitur; what a student
  actually said is never recorded.

Every claim carries an `[mm:ss]` and, when several recordings exist, which one.
Anything uncertain is marked `(uncertain)` inline, on the claim itself, with a
reason.

Three closing sections are required:

- `## Off the slides` — substantial teaching belonging to no slide. Expected to be
  non-empty; if it is empty, content has probably been forced onto slides where it
  does not belong.
- `## Unresolved` — every garbled passage that the slides could not settle, with
  timestamps. Guessing is forbidden and listing is required.
- `## Coverage` — per recording, which slides it reaches and which stretches were
  not course content; then, once for the deck, which slides no recording reaches.
  A recording of a different lecture is a legal input, described in prose, with
  only the relevant part used.

**No length target.** Both test runs exceeded the 3,000-word cap they were given
(to 3,752 and 5,068) and both reported they could only comply by cutting real
explanation. The rule is: as long as the material warrants, and never padded.

## Stage 3: additive enrichment

The pass may **add** sentences, paragraphs, sections and self-check questions,
deepen thin passages, and reorder sections so that what was stressed comes first.

It may **not remove or replace** any fact, equation, figure link, citation,
definition, code block or self-check question already present. Where the existing
text and the narration disagree, the existing text stays and the qualification is
added beside it. This is the rule that prevents the failure the experiment found:
narration-derived prose displacing correct slide-derived prose.

Two supporting rules, each from an observed failure:

- **Every added claim traces to a passage.** A connecting sentence nobody said is
  the writer's own inference: it is either omitted or marked
  `> **Beyond the slides:**`. A plausible bridge between two things he said,
  written in his voice, is a fabrication.
- **Hedges survive.** An intuition stays an intuition with its qualification. A
  hedged analogy never becomes a definition, and a number said aloud never replaces
  the slide's number.

Terminology *he* introduces that the slides lack (calling the acting policy the
behaviour policy, say) may be added, since it extends rather than contradicts.

Narration leaves no visible trace: no timestamps, no "the instructor said", no
mention of recordings or of the lecture as an event. `> **Beyond the slides:**`
stays reserved for the writer's own additions.

Sections covering slides no recording reached must come out of this pass exactly as
they went in. Absence of narration is not evidence of unimportance; in testing this
is the rule that failed most often.

## Verification: the additive invariant

`finish` snapshots `NOTES.md` on every success. When a later `finish` runs against
an existing snapshot, it reports what changed — figure links, display equations,
headings, code blocks, self-check count, and the fraction of previous sentences
still present — and **warns**, naming each item, when anything was removed. It does
not block: a deliberate rewrite is legitimate. The check needs no judgement, which
is why it belongs in the tool rather than in the instructions.

This is the mechanism that caught the earlier approach losing 11 equations and 4
code blocks, and that confirmed both enrichment runs were clean.

## Model requirements

The digest and enrichment stages need a capable model. In testing, a mid-tier model
given identical inputs fabricated a classroom event outright ("the class initially
answers no" where the transcript records nobody answering no), filed the two longest
off-slide stretches under confident slide numbers, and quoted ASR garble as the
instructor's own term. It was no more accurate than working with no slides at all,
while appearing more confident. This is documented guidance, not something the tool
enforces.

## Out of scope

- Pushing narration timestamps into the finished notes (settled: no timestamps, no
  attribution).
- Tool-side alignment of transcript to slides, in any form.
- Any repair of ASR text, whether by heuristic or by model.
- Speaker diarization, and any use of student audio beyond paraphrasing a question's
  topic.
- Video input and frame-based alignment.

## Testing

- Scale detection: 10 ms and 1 ms inputs; a file whose implied rate is plausible at
  no scale is rejected with a specific error.
- Normalization: paragraph breaks fall at pauses; no word is lost between input and
  output; untimed plain text produces no markers; SRT and WebVTT cue times are read.
- Repeated `--transcript` produces `narration-1.md`, `narration-2.md`, and a
  manifest entry each.
- `prep --force` re-normalizes transcripts and preserves `NOTES.md`.
- Instructions render the narration section only when a transcript is present.
- Snapshot/diff: a removed figure link, equation, code block and self-check question
  are each reported by name; an addition-only revision reports clean.
- Real runs: lectures 2 and 3 enrich additively, `finish` passes, and both export.

## Appendix: narration section of `INSTRUCTIONS.md`

The tested draft of the agent-facing wording, with the fixes both runs asked for,
is `docs/narration-instructions-draft.md`. It is rendered into `INSTRUCTIONS.md`
only when the workdir contains at least one transcript.
