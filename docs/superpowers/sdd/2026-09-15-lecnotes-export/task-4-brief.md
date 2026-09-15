### Task 4: Notion import zip

**Files:**
- Create: `src/lecnotes/export_notion.py`
- Test: `tests/test_export_notion.py`

**Interfaces:**
- Consumes: `mdparse.PARSER`, `markdown_doc.LocalImage`, `markdown_doc.local_images` (tests only), `png` fixture
- Produces:
  - `TITLE_MAX = 100`
  - `unwrap(markdown: str) -> str`
  - `sanitize_filename(text: str) -> str` (may return `""`)
  - `split_title(markdown: str, fallback_stem: str) -> tuple[str, str]` — `(file stem, body with that heading removed)`
  - `images_outside(images: list[LocalImage], base_dir: Path) -> list[str]` — srcs resolving outside `base_dir`, in order
  - `write_notion_zip(markdown: str, images: list[LocalImage], base_dir: Path, dest: Path, fallback_stem: str) -> None` — precondition: images exist and none are outside `base_dir`

**How unwrap works (and why not a line regex):** parse with `PARSER`; every top-level-or-list `paragraph_open` token that is *not* inside a blockquote and whose `map` spans more than one source line has its lines joined — continuation lines are stripped and appended to the previous line with one space. A line ending in a hard break (two trailing spaces or a backslash) is not joined onto. Because only paragraph line ranges are touched, fenced code, indented code, tables, headings, and blockquotes are left byte-for-byte. This replaces CS4440's line-regex `unwrap` with the same intent.

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_notion.py`:

```python
import zipfile

from lecnotes.export_notion import (
    TITLE_MAX,
    images_outside,
    sanitize_filename,
    split_title,
    unwrap,
    write_notion_zip,
)
from lecnotes.markdown_doc import local_images


def test_unwrap_joins_wrapped_paragraph_keeping_spans_intact():
    md = "A **bold\nclaim** that\nwraps.\n\nNext para.\n"
    assert unwrap(md) == "A **bold claim** that wraps.\n\nNext para.\n"


def test_unwrap_joins_list_item_continuations():
    md = "- first item\n  continues here\n- second\n"
    assert unwrap(md) == "- first item continues here\n- second\n"


def test_unwrap_leaves_code_tables_headings_and_quotes_alone():
    md = (
        "# Heading\n\n"
        "```\nline one\nline two\n```\n\n"
        "    indented\n    code\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        "> quoted\n> lines\n"
    )
    assert unwrap(md) == md


def test_unwrap_preserves_hard_breaks():
    md = "line one  \nline two\\\nline three\nline four\n"
    assert unwrap(md) == "line one  \nline two\\\nline three line four\n"


def test_sanitize_filename():
    assert sanitize_filename('  B+ Trees: why/how? "fast" <1> | *2*  ') == 'B+ Trees- why-how- -fast- -1- - -2-'
    assert len(sanitize_filename("x" * 300)) == TITLE_MAX
    assert sanitize_filename("   ") == ""


def test_split_title_uses_first_h1_and_removes_it():
    md = "# Imitation Learning\n\nIntro text.\n\n# Second H1 stays\n"
    stem, body = split_title(md, "lec1")
    assert stem == "Imitation Learning"
    assert body == "Intro text.\n\n# Second H1 stays\n"


def test_split_title_strips_inline_markup():
    stem, _ = split_title("# B+ *Trees*\n\ntext\n", "lec1")
    assert stem == "B+ Trees"


def test_split_title_falls_back_without_h1():
    md = "## Only h2\n\ntext\n"
    assert split_title(md, "lec1") == ("lec1", md)


def test_split_title_falls_back_when_title_sanitizes_to_empty():
    stem, body = split_title("# ///\n\ntext\n", "lec1")
    assert stem == "---"  # slashes become dashes, which is not empty
    stem, body = split_title("#    \n\ntext\n", "lec1")
    assert stem == "lec1"


def test_images_outside(tmp_path, png):
    notes = tmp_path / "notes"
    notes.mkdir()
    md = "![a](figures/x.png) ![b](../shared/y.png) ![c](./z.png)\n"
    assert images_outside(local_images(md, notes), notes) == ["../shared/y.png"]


def test_write_notion_zip_layout(tmp_path, png):
    base = tmp_path / "out"
    png(base / "figures" / "slide-001.png")
    png(base / "figures" / "slide-002.png")
    md = (
        "# Learning from Data\n\n"
        "Some wrapped\nprose.\n\n"
        "![one](figures/slide-001.png)\n\n"
        "![two](./figures/slide-002.png)\n\n"
        "![one again](figures/slide-001.png)\n"
    )
    dest = base / "lec1-notion.zip"
    write_notion_zip(md, local_images(md, base), base, dest, "lec1")

    with zipfile.ZipFile(dest) as zf:
        assert sorted(zf.namelist()) == [
            "Learning from Data.md",
            "figures/slide-001.png",
            "figures/slide-002.png",
        ]
        text = zf.read("Learning from Data.md").decode("utf-8")
    assert not text.startswith("# Learning from Data")
    assert "Some wrapped prose." in text
    assert "![one](figures/slide-001.png)" in text
    assert not (base / "lec1-notion.zip.tmp").exists()


def test_write_notion_zip_overwrites(tmp_path):
    dest = tmp_path / "n.zip"
    dest.write_bytes(b"old")
    write_notion_zip("# T\n\nbody\n", [], tmp_path, dest, "n")
    with zipfile.ZipFile(dest) as zf:
        assert zf.namelist() == ["T.md"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_export_notion.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.export_notion'`

- [ ] **Step 3: Implement**

Create `src/lecnotes/export_notion.py`:

```python
"""Markdown to a zip Notion's importer understands (Settings > Import > Markdown).

Notion resolves relative image links inside an imported zip, so the package is
just the Markdown plus its images at the same relative paths.
"""

import re
import zipfile
from pathlib import Path

from .markdown_doc import LocalImage
from .mdparse import PARSER

TITLE_MAX = 100
_UNSAFE_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|]')


def unwrap(markdown: str) -> str:
    """Join hard-wrapped paragraph lines.

    Notion merges wrapped lines into one paragraph but does not re-parse inline
    spans across the break, so `**bold**` split over two lines shows literal
    asterisks. Only paragraph line ranges are touched; code, tables, headings and
    blockquotes are left exactly as written.
    """
    lines = markdown.split("\n")
    ranges = []
    quote_depth = 0
    for token in PARSER.parse(markdown):
        if token.type == "blockquote_open":
            quote_depth += 1
        elif token.type == "blockquote_close":
            quote_depth -= 1
        elif (
            token.type == "paragraph_open"
            and quote_depth == 0
            and token.map
            and token.map[1] - token.map[0] > 1
        ):
            ranges.append(token.map)

    for start, end in reversed(ranges):
        joined = [lines[start]]
        for line in lines[start + 1 : end]:
            previous = joined[-1]
            if previous.endswith("  ") or previous.endswith("\\"):
                joined.append(line)  # a hard line break the author meant
            else:
                joined[-1] = previous.rstrip() + " " + line.strip()
        lines[start:end] = joined
    return "\n".join(lines)


def sanitize_filename(text: str) -> str:
    return _UNSAFE_FILENAME_CHARS.sub("-", text).strip()[:TITLE_MAX].strip()


def split_title(markdown: str, fallback_stem: str) -> tuple[str, str]:
    """Name the page after the first top-level H1, and drop that heading.

    Notion titles an imported page after its file name; keeping the heading too
    would show the title twice.
    """
    tokens = PARSER.parse(markdown)
    for i, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h1" and token.level == 0:
            text = PARSER.renderer.renderInlineAsText(
                tokens[i + 1].children or [], PARSER.options, {}
            )
            stem = sanitize_filename(text)
            if not stem or not token.map:
                return fallback_stem, markdown
            lines = markdown.split("\n")
            start, end = token.map
            del lines[start:end]
            return stem, "\n".join(lines).lstrip("\n")
    return fallback_stem, markdown


def images_outside(images: list[LocalImage], base_dir: Path) -> list[str]:
    """Srcs that climb out of base_dir; a zip entry cannot safely point there."""
    base = Path(base_dir).resolve()
    return [image.src for image in images if not image.path.is_relative_to(base)]


def write_notion_zip(
    markdown: str,
    images: list[LocalImage],
    base_dir: Path,
    dest: Path,
    fallback_stem: str,
) -> None:
    """Write the zip. Images must exist and lie inside base_dir."""
    stem, body = split_title(markdown, fallback_stem)
    base = Path(base_dir).resolve()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    tmp = dest.with_name(dest.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{stem}.md", unwrap(body))
        # Two srcs can name one file (figures/x.png and ./figures/x.png).
        for path in dict.fromkeys(image.path for image in images):
            zf.write(path, path.relative_to(base).as_posix())
    tmp.replace(dest)
```

Note on `test_split_title_falls_back_when_title_sanitizes_to_empty`: `# ///` sanitizes to `---` (not empty), and a heading with only whitespace has empty text, which falls back.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_export_notion.py -v` → PASS. If markdown-it's `map` for a list-item paragraph differs from the test's expectation, keep the tested behavior (wrapped continuation lines joined onto the item line) and report the deviation. Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 5: Commit**

```bash
git add src/lecnotes/export_notion.py tests/test_export_notion.py
git commit -m "Package Markdown and its images as a Notion import zip"
```

---

