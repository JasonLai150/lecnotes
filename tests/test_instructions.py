from lecnotes.instructions import render_instructions


def rendered(**kw):
    args = dict(deck="lec1", slides=47, figures=29, source_name="lec1.pdf")
    args.update(kw)
    return render_instructions(**args)


def test_states_the_deck_and_counts():
    out = rendered()
    assert "lec1" in out
    assert "47" in out
    assert "29" in out


def test_shows_the_exact_figure_link_syntax():
    assert "![" in rendered() and "](figures/slide-NNN.png)" in rendered()


def test_names_the_file_to_write():
    assert "NOTES.md" in rendered()


def test_names_the_command_to_run_when_done():
    """Run from inside the workdir, so it holds wherever the workdir lives."""
    out = rendered()
    assert "    lecnotes finish .\n" in out
    assert "from inside this directory" in out
    assert "lec1.notes" not in out


def test_points_at_both_the_png_and_the_txt():
    out = rendered()
    assert "pages/slide-001.png" in out
    assert "pages/slide-001.txt" in out


def test_no_unreplaced_placeholders():
    out = rendered()
    assert "{" not in out.replace("{{", "").replace("}}", "")
    assert "$" not in out


def test_warns_that_figure_links_use_figures_not_pages():
    assert "not `pages/`" in rendered()
