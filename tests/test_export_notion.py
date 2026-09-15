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
