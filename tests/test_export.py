import zipfile

import pytest

from lecnotes import workdir
from lecnotes.commands import export, finish, prep
from lecnotes.errors import LecnotesError


@pytest.fixture
def finished(synth, tmp_path):
    """A prepped and finished 3-slide workdir with one figure."""
    pdf = synth(tmp_path / "lec1.pdf", [{"text": f"S{i}", "small_box": (100, 100, 300, 220)}
                                        for i in range(1, 4)])
    prep(pdf)
    root = tmp_path / "lec1.notes"
    workdir.notes_path(root).write_text(
        "# Lecture One\n\nWrapped\nprose.\n\n![node](figures/slide-002.png)\n", encoding="utf-8"
    )
    finish(root)
    return root


def test_html_from_workdir(finished):
    result = export(finished, "html")
    out = workdir.out_dir(finished) / "lec1.html"
    assert result == {
        "ok": True,
        "format": "html",
        "source": str(workdir.out_dir(finished) / "lec1.md"),
        "output": str(out),
        "images": 1,
        "bytes": out.stat().st_size,
    }
    html = out.read_text(encoding="utf-8")
    assert "data:image/png;base64," in html and "<title>Lecture One</title>" in html


def test_notion_from_workdir(finished):
    result = export(finished, "notion")
    out = workdir.out_dir(finished) / "lec1-notion.zip"
    assert result["output"] == str(out) and result["images"] == 1
    with zipfile.ZipFile(out) as zf:
        assert sorted(zf.namelist()) == ["Lecture One.md", "figures/slide-002.png"]


def test_markdown_file_directly(tmp_path, png):
    png(tmp_path / "img" / "a.png")
    md = tmp_path / "edited.md"
    md.write_text("# E\n\n![a](img/a.png)\n", encoding="utf-8")
    result = export(md, "html")
    assert result["output"] == str(tmp_path / "edited.html")
    assert result["source"] == str(md)


def test_out_option_and_overwrite(tmp_path):
    md = tmp_path / "n.md"
    md.write_text("text\n", encoding="utf-8")
    dest = tmp_path / "deep" / "dir" / "custom.html"
    export(md, "html", out=dest)
    first = dest.read_text()
    md.write_text("changed\n", encoding="utf-8")
    export(md, "html", out=dest)
    assert dest.read_text() != first


def test_source_not_found(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path / "nope.md", "html")
    assert exc.value.code == "source_not_found"


@pytest.mark.parametrize("name", ["notes.txt", "deck.pdf"])
def test_non_markdown_file_is_unsupported(tmp_path, name):
    (tmp_path / name).write_text("x")
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path / name, "html")
    assert exc.value.code == "unsupported_format"


def test_plain_directory_is_unsupported(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path, "html")
    assert exc.value.code == "unsupported_format"


def test_workdir_before_finish(synth, tmp_path):
    prep(synth(tmp_path / "lec1.pdf", [{"text": "a"}]))
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path / "lec1.notes", "html")
    assert exc.value.code == "not_finished"
    assert "finish" in exc.value.message


def test_workdir_with_notes_edited_after_finish(finished):
    workdir.notes_path(finished).write_text("# Lecture One\n\nnewer\n", encoding="utf-8")
    with pytest.raises(LecnotesError) as exc:
        export(finished, "notion")
    assert exc.value.code == "not_finished"
    assert "NOTES.md" in exc.value.message
    assert not (workdir.out_dir(finished) / "lec1-notion.zip").exists()


def test_missing_images_all_listed_nothing_written(tmp_path, png):
    png(tmp_path / "ok.png")
    md = tmp_path / "n.md"
    md.write_text("![a](gone1.png) ![b](ok.png) ![c](gone2.png) ![d](gone1.png)\n")
    with pytest.raises(LecnotesError) as exc:
        export(md, "html")
    assert exc.value.code == "image_not_found"
    assert exc.value.detail["missing"] == ["gone1.png", "gone2.png"]
    assert not (tmp_path / "n.html").exists()


def test_outside_root_rejected_for_notion_only(tmp_path, png):
    png(tmp_path / "shared" / "x.png")
    notes = tmp_path / "notes"
    notes.mkdir()
    md = notes / "n.md"
    md.write_text("![x](../shared/x.png)\n")

    with pytest.raises(LecnotesError) as exc:
        export(md, "notion")
    assert exc.value.code == "image_outside_root"
    assert exc.value.detail["outside"] == ["../shared/x.png"]
    assert not (notes / "n-notion.zip").exists()

    assert export(md, "html")["images"] == 1


def test_exporters_never_modify_the_markdown(finished):
    md = workdir.out_dir(finished) / "lec1.md"
    before = md.read_bytes()
    export(finished, "html")
    export(finished, "notion")
    assert md.read_bytes() == before


@pytest.mark.parametrize("fmt", ["html", "notion"])
def test_out_equal_to_source_is_rejected(tmp_path, fmt):
    md = tmp_path / "n.md"
    md.write_text("text\n", encoding="utf-8")
    before = md.read_bytes()

    with pytest.raises(LecnotesError) as exc:
        export(md, fmt, out=md)
    assert exc.value.code == "invalid_output"
    assert md.read_bytes() == before


def test_out_equal_to_workdir_output_is_rejected(finished):
    out_md = workdir.out_dir(finished) / "lec1.md"
    before = out_md.read_bytes()

    with pytest.raises(LecnotesError) as exc:
        export(finished, "notion", out=out_md)
    assert exc.value.code == "invalid_output"
    assert out_md.read_bytes() == before


@pytest.mark.parametrize("fmt", ["html", "notion"])
def test_out_is_existing_directory_is_rejected(tmp_path, fmt, png):
    png(tmp_path / "ok.png")
    md = tmp_path / "n.md"
    md.write_text("![a](ok.png)\n", encoding="utf-8")
    target_dir = tmp_path / "somedir"
    target_dir.mkdir()

    with pytest.raises(LecnotesError) as exc:
        export(md, fmt, out=target_dir)
    assert exc.value.code == "invalid_output"
    assert list(target_dir.iterdir()) == []
