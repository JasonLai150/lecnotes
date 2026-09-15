### Task 6: README and a real export

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the finished CLI
- Produces: nothing importable

- [ ] **Step 1: Export real lecture notes**

The real notes live in the user's workdir `DRL lectures/lec-1-cs8803-drl-f26-supervised-learning.notes` inside the repo (git-ignored). Do not modify anything in it. Copy it to the scratchpad first, then export the copy:

```bash
SCRATCH=/private/tmp/claude-501/-Users-jasonlai150-Documents-GitHub-4440/b8ce7be5-28b5-4a05-868b-6c0cf5495ca3/scratchpad
rm -rf "$SCRATCH/export-e2e" && mkdir -p "$SCRATCH/export-e2e"
cp -R "/Users/jasonlai150/Documents/GitHub/lecnotes/DRL lectures/lec-1-cs8803-drl-f26-supervised-learning.notes" "$SCRATCH/export-e2e/"
cd "$SCRATCH/export-e2e/lec-1-cs8803-drl-f26-supervised-learning.notes"
uv --project /Users/jasonlai150/Documents/GitHub/lecnotes run lecnotes export . --to html --json
uv --project /Users/jasonlai150/Documents/GitHub/lecnotes run lecnotes export . --to notion --json
```

If `export` reports `not_finished`, run `lecnotes finish .` on the **copy** and retry. Record every command and its output.

Then verify:
- the HTML has as many `data:image/png;base64,` occurrences as the notes have distinct figure links (`grep -o 'data:image/png;base64,' out/*.html | wc -l`), no `src="figures/`, and no `http`;
- `unzip -l out/*-notion.zip` lists one `.md` named after the notes' first heading plus every `figures/slide-NNN.png`;
- the `.md` inside the zip (`unzip -p out/*-notion.zip '*.md' | head -20`) starts after the title and has no hard-wrapped paragraphs.

- [ ] **Step 2: Add an Export section to README.md**

Add after the section that documents `finish` (keep the rest of the README unchanged):

````markdown
## Export

The Markdown `finish` writes is the source of truth. `export` turns it into
something easier to read or share, without changing it:

```sh
lecnotes export lec13.notes --to html     # lec13.notes/out/lec13.html
lecnotes export lec13.notes --to notion   # lec13.notes/out/lec13-notion.zip
```

- **HTML** is one self-contained file: figures are embedded, styles are inline,
  there is no JavaScript and nothing loads from the network. Open it in any
  browser, or print it to PDF.
- **Notion**: in Notion, go to Settings → Import → Markdown and choose the zip.
  The page is named after the notes' title, and figures come through. (Pasting
  the `.md` alone loses the images; the zip keeps them together.)

`export` also accepts any `.md` file, resolving images relative to it, and `-o`
sets the output path. On a workdir it refuses to export notes that have changed
since the last `finish`, so you never share a stale copy.
````

Also add the three new codes to any error-code list in the README, if the README has one.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Document export"
```

---

## Verification

- [ ] `uv run pytest -q` passes with no warnings
- [ ] `uv run lecnotes export --help` renders
- [ ] Task 6's real export produced an HTML file with every figure embedded and a zip with the titled `.md` plus all figures
