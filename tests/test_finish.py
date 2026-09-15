import pytest

from lecnotes import workdir
from lecnotes.commands import finish, prep
from lecnotes.errors import LecnotesError


@pytest.fixture
def prepared(synth, tmp_path):
    """A prepped 5-slide workdir, ready for notes to be written into."""
    pdf = synth(
        tmp_path / "lec1.pdf",
        [{"text": f"Slide {i}", "small_box": (100, 100, 300, 220)} for i in range(1, 6)],
    )
    prep(pdf)
    return tmp_path / "lec1.notes"


def write_notes(root, body):
    workdir.notes_path(root).write_text(body, encoding="utf-8")


def test_assembles_the_output_document(prepared):
    write_notes(prepared, "# B+ Trees\n\nFanout buys shallowness.\n")
    result = finish(prepared)
    out = workdir.out_dir(prepared) / "lec1.md"
    assert out.is_file()
    assert "Fanout buys shallowness." in out.read_text()
    assert result["output"] == str(out)
    assert result["ok"] is True


def test_resolves_and_crops_referenced_figures(prepared):
    write_notes(prepared, "# T\n\n![the node](figures/slide-003.png)\n")
    result = finish(prepared)
    assert result["figures_resolved"] == 1
    assert (workdir.out_figures_dir(prepared) / "slide-003.png").is_file()


def test_only_referenced_slides_are_copied(prepared):
    write_notes(prepared, "![a](figures/slide-002.png)\n![b](figures/slide-004.png)\n")
    finish(prepared)
    names = sorted(p.name for p in workdir.out_figures_dir(prepared).glob("*.png"))
    assert names == ["slide-002.png", "slide-004.png"]


def test_notes_with_no_figures_still_builds(prepared):
    write_notes(prepared, "# All prose\n")
    assert finish(prepared)["figures_resolved"] == 0


def test_out_of_range_reference_is_named(prepared):
    write_notes(prepared, "![x](figures/slide-091.png)\n")
    with pytest.raises(LecnotesError) as exc:
        finish(prepared)
    assert exc.value.code == "figure_out_of_range"
    assert exc.value.exit_code == 1
    assert exc.value.detail["bad_refs"] == [{"slide": 91, "max": 5}]


def test_every_bad_reference_is_reported_not_just_the_first(prepared):
    write_notes(prepared, "![x](figures/slide-091.png)\n![y](figures/slide-007.png)\n")
    with pytest.raises(LecnotesError) as exc:
        finish(prepared)
    assert exc.value.detail["bad_refs"] == [{"slide": 7, "max": 5}, {"slide": 91, "max": 5}]


def test_nothing_is_written_when_validation_fails(prepared):
    write_notes(prepared, "![x](figures/slide-091.png)\n")
    with pytest.raises(LecnotesError):
        finish(prepared)
    assert not workdir.out_dir(prepared).exists()


def test_malformed_figure_link_is_named(prepared):
    write_notes(
        prepared,
        "![a](pages/slide-002.png)\n![ok](figures/slide-001.png)\n"
        "![b](figures/slide-3.png)\n![c](pages/slide-002.png)\n",
    )
    with pytest.raises(LecnotesError) as exc:
        finish(prepared)
    assert exc.value.code == "figure_malformed"
    assert exc.value.exit_code == 1
    assert exc.value.detail["bad_links"] == ["pages/slide-002.png", "figures/slide-3.png"]
    assert not workdir.out_dir(prepared).exists()


def test_malformed_links_are_reported_before_out_of_range_ones(prepared):
    """Both are checked before anything is written; malformed wins when both occur."""
    write_notes(prepared, "![x](figures/slide-091.png)\n![y](pages/slide-002.png)\n")
    with pytest.raises(LecnotesError) as exc:
        finish(prepared)
    assert exc.value.code == "figure_malformed"
    assert exc.value.detail["bad_links"] == ["pages/slide-002.png"]
    assert not workdir.out_dir(prepared).exists()


def test_bracket_in_caption_does_not_drop_the_figure(prepared):
    write_notes(prepared, "# T\n\n![E_{x~p}[f(x)] estimator](figures/slide-003.png)\n")
    result = finish(prepared)
    assert result["figures_resolved"] == 1
    assert (workdir.out_figures_dir(prepared) / "slide-003.png").is_file()


def test_unbalanced_bracket_in_caption_is_malformed(prepared):
    write_notes(prepared, "![maps [0,1) to R](figures/slide-004.png)\n")
    with pytest.raises(LecnotesError) as exc:
        finish(prepared)
    assert exc.value.code == "figure_malformed"
    assert not workdir.out_dir(prepared).exists()


def test_unwritten_notes_are_refused(prepared):
    with pytest.raises(LecnotesError) as exc:
        finish(prepared)
    assert exc.value.code == "notes_empty"
    assert exc.value.exit_code == 1


def test_non_workdir_is_refused(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        finish(tmp_path)
    assert exc.value.code == "not_a_workdir"


@pytest.mark.parametrize("manifest", ['{"name": "my pwa"}', "{not json"])
def test_directory_with_a_manifest_that_is_not_ours_is_refused(tmp_path, manifest):
    (tmp_path / "manifest.json").write_text(manifest)
    (tmp_path / "NOTES.md").write_text("# Notes\n")
    with pytest.raises(LecnotesError) as exc:
        finish(tmp_path)
    assert exc.value.code == "not_a_workdir"


def test_rebuild_clears_stale_figures(prepared):
    write_notes(prepared, "![a](figures/slide-002.png)\n")
    finish(prepared)
    write_notes(prepared, "![b](figures/slide-004.png)\n")
    finish(prepared)
    names = sorted(p.name for p in workdir.out_figures_dir(prepared).glob("*.png"))
    assert names == ["slide-004.png"]


def test_punctuated_deck_name_flows_through_to_the_output_file(synth, tmp_path):
    pdf = synth(tmp_path / "lec8-txn,cc.pdf", [{"text": "Locks", "small_box": (100, 100, 300, 220)}])
    root = tmp_path / "lec8-txn-cc.notes"
    assert prep(pdf)["workdir"] == str(root)
    write_notes(root, "# Concurrency control\n\n![a lock](figures/slide-001.png)\n")
    result = finish(root)
    assert result["output"] == str(workdir.out_dir(root) / "lec8-txn-cc.md")
    assert (workdir.out_dir(root) / "lec8-txn-cc.md").is_file()
