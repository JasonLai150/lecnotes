# Task 13 report: end-to-end check against a real deck, and the README

## What I implemented

No production code changes (this task has no TDD cycle). I ran the four
end-to-end steps from the brief against the real CS4440 deck
`/Users/jasonlai150/Documents/GitHub/4440/slides/lec13-b+tree.pdf`, observed
the tool's behavior on real content, and then created `README.md` verbatim
from the brief's Step 4 text.

## Pre-flight

```
$ cd /Users/jasonlai150/Documents/GitHub/lecnotes && uv run pytest -q
........................................................................ [ 73%]
..........................                                               [100%]
98 passed, 5 warnings in 2.08s
```

`--help` for all three entry points rendered correctly (`lecnotes --help`,
`lecnotes prep --help`, `lecnotes finish --help`), each exiting 0.

I also re-confirmed the Task-12 review fix that usage errors exit 1, not 2,
since the brief said the README must stay accurate to that:

```
$ uv run lecnotes prep; echo "exit=$?"
usage: lecnotes prep [-h] [-o OUT] [--force] [--json] source
lecnotes prep: error: the following arguments are required: source
exit=1

$ uv run lecnotes finish; echo "exit=$?"
usage: lecnotes finish [-h] [--json] workdir
lecnotes finish: error: the following arguments are required: workdir
exit=1

$ uv run lecnotes bogus; echo "exit=$?"
lecnotes: error: argument command: invalid choice: 'bogus' (choose from 'prep', 'finish')
exit=1
```

The README's existing exit-code line ("`0` success, `1` usage or validation
failure, `2` missing external dependency") is accurate as-is; no change
needed.

## Step 1: run against the real deck

```
$ uv run lecnotes prep ~/Documents/GitHub/4440/slides/lec13-b+tree.pdf -o \
    /private/tmp/claude-501/-Users-jasonlai150-Documents-GitHub-4440/b8ce7be5-28b5-4a05-868b-6c0cf5495ca3/scratchpad/lec13.notes
/private/tmp/.../scratchpad/lec13.notes
  52 slides, 46 with figures
  read  .../INSTRUCTIONS.md
  write .../NOTES.md
  then  lecnotes finish .../lec13.notes
exit=0
```

52 slides, 46 with figures — both non-zero, as expected. The workdir did not
already exist so `--force` was not needed for this first run.

`manifest.json` confirms `"deck": "lec13-b-tree"` (matching the brief's
stated slug), `"slides": 52`, `"figures": 46`, and slide 8 is flagged
`"figure": true`.

`INSTRUCTIONS.md` reads sensibly — it names the deck (`lec13-b-tree`),
states 52 slides / 46 with figures, explains what to read and write, and how
to link figures. Checked for leftover template placeholders:

```
$ grep -n '\$placeholder' .../lec13.notes/INSTRUCTIONS.md
(no output — none found)
```

Opened `pages/slide-008.png` with the Read tool: it is legible — a "B+ Tree
Basics" title slide showing an interior node diagram (a 4-cell node with
keys 10/20/30, arrows into four labeled ranges, and a yellow annotation
box). Dimensions: **1400 x 788** (PNG, confirmed via `file`).

## Step 2: verify the crop on real content

```
$ cd .../lec13.notes
$ printf '# B+ Trees\n\n![an interior node](figures/slide-008.png)\n' > NOTES.md
$ uv --project ~/Documents/GitHub/lecnotes run lecnotes finish .../lec13.notes
.../lec13.notes/out/lec13-b-tree.md
  1 figures resolved
exit=0
```

`out/lec13-b-tree.md` and `out/figures/slide-008.png` both exist.

Dimensions:
- `pages/slide-008.png` (full page): **1400 x 788**
- `out/figures/slide-008.png` (crop): **1400 x 593**

Opened both with the Read tool. The full page has the diagram occupying
roughly the top three-quarters of the frame, with a large blank white
margin below the "10 ≤ k < 20" annotation extending down to the bottom of
the 788px-tall page. The crop keeps the full width (1400px, since the
content spans nearly edge to edge horizontally) but cuts the height to
593px, ending right after the lowest annotation text — the blank ~195px
bottom margin is gone. This is the content-box backdrop filter working on a
real deck: the full-page white backdrop is excluded, and the crop tightens
to the actual ink.

## Step 3: verify the failure path on the real deck

```
$ printf '![x](figures/slide-991.png)\n' > .../lec13.notes/NOTES.md
$ uv --project ~/Documents/GitHub/lecnotes run lecnotes finish .../lec13.notes --json; echo "exit=$?"
{"ok": false, "error": "figure_out_of_range", "bad_refs": [{"slide": 991, "max": 52}]}
exit=1
```

Exit 1, and the JSON names slide 991 against the deck's real slide count
(52) — exactly as expected.

## Sanity check: README's JSON example schema

Re-ran `prep --force --json` on the same workdir to confirm the emitted key
set matches the shape documented in the README's "For agents" section:

```
{"ok": true, "workdir": "...", "deck": "lec13-b-tree", "slides": 52,
 "figures": 46, "notes_preserved": true, "instructions": "...",
 "write_to": "...", "next": "lecnotes finish ..."}
```

Same keys as the README's example (`ok`, `workdir`, `deck`, `slides`,
`figures`, `notes_preserved`, `instructions`, `write_to`, `next`). No
mismatch.

## Step 4: README.md

Created `/Users/jasonlai150/Documents/GitHub/lecnotes/README.md` with the
exact content given in the brief's Step 4 (Install, Use, For agents, Why
slides get rendered rather than parsed, Development sections). No wording
changes — the brief's content matched everything I verified in Steps 1-3
(exit codes, JSON shape, figure-link form).

## Files changed

- `README.md` (new)

## Deviations from the brief

None. The tool behaved exactly as the brief predicted on the real deck: a
non-zero slide/figure count, a legible rendered page, an `INSTRUCTIONS.md`
free of template placeholders, a visibly tighter crop on real content, and a
correct out-of-range failure naming the real slide count.

## Self-review

- README content is copied verbatim from the brief (Step 4), which I
  cross-checked line-by-line against actual CLI output (exit codes, JSON
  keys) before committing — no drift.
- Confirmed via `git status`/`find -newer` that nothing under
  `/Users/jasonlai150/Documents/GitHub/4440` was modified; the 4440
  directory has no `.git` of its own and only `lec13-b+tree.pdf` was read.
- Confirmed only `README.md` was staged (`git status --short` before
  commit showed `A  README.md` only) — the scratchpad workdir under
  `/private/tmp/...` is outside the lecnotes repo and was not touched by
  git.
- Full suite re-run before committing: 98 passed, no failures, no skips.
- `git log --oneline` shows the new `Add README` commit on top of the
  existing per-task history.

## Concerns

None. The real deck exposed no bugs — the figure-detection heuristic, crop,
slide count, and error path all behaved as designed on real Keynote-exported
content.
