from lecnotes.instructions import render_instructions


def rendered(**kw):
    args = dict(deck="lec1", slides=47, source_name="lec1.pdf")
    args.update(kw)
    return render_instructions(**args)


def test_states_the_deck_and_slide_count():
    out = rendered()
    assert "lec1" in out
    assert "47" in out


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
    assert "{{" not in out and "}}" not in out


def test_equations_are_latex():
    out = rendered()
    assert "$\\pi_\\theta(a_t \\mid s_t)$" in out
    assert "\n    $$\n" in out
    assert "\\$" in out  # how to write a literal dollar
    assert "code spans" in out


def test_no_plain_text_equation_wording():
    assert "Type every equation as plain text" not in rendered()


def test_values_containing_braces_or_dollars_are_inserted_verbatim():
    out = rendered(deck="lec-{x}$", source_name="$deck{{slides}}.pdf")
    assert "lec-{x}$" in out
    assert "$deck{{slides}}.pdf" in out


def test_warns_that_figure_links_use_figures_not_pages():
    assert "not `pages/`" in rendered()


def test_tells_the_agent_to_view_every_slide_image():
    assert "View every slide image" in rendered()


def test_marks_additions_beyond_the_slides():
    assert "Beyond the slides" in rendered()


def test_calls_algorithms_pseudocode():
    assert "pseudocode" in rendered()


def test_names_the_deck_source_file_and_the_original_name():
    out = rendered(source_name="cs4440-lec3.pptx")
    assert "source.pdf" in out
    assert "cs4440-lec3.pptx" in out


def test_no_figure_flag_wording_remains():
    out = rendered()
    assert "repay a close look" not in out
    assert "hint, not a filter" not in out


def test_display_math_must_be_flush_left():
    out = rendered()
    assert "flush left" in out
