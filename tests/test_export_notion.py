import zipfile

import pytest

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
    # Whitespace runs collapse (the two leading/trailing spaces become one each),
    # "Trees: why" becomes "Trees - why" (colon rule), then / ? " < > | * each
    # become "-": "why-how-", "-fast-", "-1-", "-", "-2-"; finally the ends are trimmed.
    assert (
        sanitize_filename('  B+ Trees: why/how? "fast" <1> | *2*  ')
        == "B+ Trees - why-how- -fast- -1- - -2-"
    )
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


def test_sanitize_filename_colon_becomes_spaced_dash():
    assert sanitize_filename("Learning from Data: Imitation") == "Learning from Data - Imitation"
    assert sanitize_filename("a:b") == "a - b"


def test_sanitize_filename_collapses_whitespace_and_drops_controls():
    assert sanitize_filename("Tab\there\x01 and\x7f\n\nnewlines") == "Tab here and newlines"


def test_setext_title_gives_one_line_name():
    stem, body = split_title("Learning from Data:\nImitation\n===\n\nbody\n", "lec1")
    assert stem == "Learning from Data - Imitation"
    assert body == "body\n"


def test_absolute_src_is_outside_even_when_inside_base_dir(tmp_path, png):
    png(tmp_path / "figures" / "x.png")
    src = str(tmp_path / "figures" / "x.png")
    images = local_images(f"![a](<{src}>) ![b](figures/x.png)\n", tmp_path)
    assert images_outside(images, tmp_path) == [images[0].src]


def test_src_that_climbs_back_in_is_still_outside(tmp_path, png):
    notes = tmp_path / "notes"
    png(notes / "x.png")
    images = local_images("![a](../notes/x.png) ![b](sub/../x.png)\n", notes)
    assert images_outside(images, notes) == ["../notes/x.png"]


def test_symlinked_figure_is_stored_under_its_link_name(tmp_path, png):
    base = tmp_path / "out"
    data = png(base / "cache" / "abc.png").read_bytes()
    (base / "figures").mkdir()
    (base / "figures" / "slide-001.png").symlink_to(base / "cache" / "abc.png")
    md = "# T\n\n![one](figures/slide-001.png)\n"
    dest = base / "n.zip"
    write_notion_zip(md, local_images(md, base), base, dest, "n")
    with zipfile.ZipFile(dest) as zf:
        assert sorted(zf.namelist()) == ["T.md", "figures/slide-001.png"]
        assert zf.read("figures/slide-001.png") == data


def test_equivalent_srcs_make_one_entry(tmp_path, png):
    png(tmp_path / "figures" / "x.png")
    md = "![a](./figures/x.png) ![b](figures/x.png)\n"
    dest = tmp_path / "n.zip"
    write_notion_zip(md, local_images(md, tmp_path), tmp_path, dest, "n")
    with zipfile.ZipFile(dest) as zf:
        assert sorted(zf.namelist()) == ["figures/x.png", "n.md"]


def test_failed_zip_write_leaves_no_tmp(tmp_path, png, monkeypatch):
    png(tmp_path / "x.png")
    md = "![a](x.png)\n"
    images = local_images(md, tmp_path)

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(zipfile.ZipFile, "write", boom)
    dest = tmp_path / "n.zip"
    with pytest.raises(OSError, match="disk full"):
        write_notion_zip(md, images, tmp_path, dest, "n")
    assert not (tmp_path / "n.zip.tmp").exists()
    assert not dest.exists()
