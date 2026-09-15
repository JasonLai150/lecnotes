import pymupdf


def test_synth_makes_a_pdf_with_the_right_page_count(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"text": "one"}, {"text": "two"}])
    doc = pymupdf.open(path)
    assert len(doc) == 2
    doc.close()


def test_text_page_has_extractable_text(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"text": "hello slides"}])
    doc = pymupdf.open(path)
    assert "hello slides" in doc[0].get_text()
    doc.close()


def test_blank_page_has_no_text(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"blank": True}])
    doc = pymupdf.open(path)
    assert doc[0].get_text().strip() == ""
    doc.close()


def test_backdrop_page_has_a_near_full_page_drawing(synth, tmp_path):
    path = synth(tmp_path / "d.pdf", [{"backdrop": True, "small_box": (100, 100, 200, 180)}])
    doc = pymupdf.open(path)
    page = doc[0]
    areas = [d["rect"].get_area() / page.rect.get_area() for d in page.get_drawings()]
    assert any(a >= 0.95 for a in areas), "expected a full-page backdrop"
    assert any(a < 0.5 for a in areas), "expected a small diagram too"
    doc.close()


def test_deck_47_has_47_pages(deck_47):
    doc = pymupdf.open(deck_47)
    assert len(doc) == 47
    doc.close()
