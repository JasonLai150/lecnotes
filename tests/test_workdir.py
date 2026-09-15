import pytest

from lecnotes import workdir
from lecnotes.errors import LecnotesError


def test_page_paths_zero_pad_to_three_digits(tmp_path):
    assert workdir.page_png(tmp_path, 8).name == "slide-008.png"
    assert workdir.page_txt(tmp_path, 8).name == "slide-008.txt"
    assert workdir.page_png(tmp_path, 147).name == "slide-147.png"


def test_relative_page_paths_are_posix(tmp_path):
    assert workdir.rel_png(8) == "pages/slide-008.png"
    assert workdir.rel_txt(8) == "pages/slide-008.txt"


def test_named_paths_hang_off_the_root(tmp_path):
    assert workdir.manifest_path(tmp_path) == tmp_path / "manifest.json"
    assert workdir.source_path(tmp_path) == tmp_path / "source.pdf"
    assert workdir.notes_path(tmp_path) == tmp_path / "NOTES.md"
    assert workdir.instructions_path(tmp_path) == tmp_path / "INSTRUCTIONS.md"
    assert workdir.out_figures_dir(tmp_path) == tmp_path / "out" / "figures"


def test_is_workdir_requires_a_manifest(tmp_path):
    assert not workdir.is_workdir(tmp_path)
    workdir.save_manifest(tmp_path, {"deck": "d"})
    assert workdir.is_workdir(tmp_path)


def test_require_workdir_raises_when_absent(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        workdir.require_workdir(tmp_path)
    assert exc.value.code == "not_a_workdir"
    assert exc.value.exit_code == 1


def test_manifest_roundtrips(tmp_path):
    data = {"deck": "lec1", "slides": 47, "pages": [{"n": 1, "chars": 31, "figure": False}]}
    workdir.save_manifest(tmp_path, data)
    assert workdir.load_manifest(tmp_path) == data


def test_manifest_is_readable_json(tmp_path):
    workdir.save_manifest(tmp_path, {"deck": "lec1"})
    assert '"deck": "lec1"' in workdir.manifest_path(tmp_path).read_text()
