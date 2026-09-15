from lecnotes.markdown_doc import (
    IMAGE_TYPES,
    find_images,
    is_external,
    local_images,
    missing_images,
)


def test_find_images_in_order_deduplicated():
    md = "![a](b.png)\n\n![c](a.png) ![d](b.png)\n"
    assert find_images(md) == ["b.png", "a.png"]


def test_find_images_ignores_code_and_plain_links():
    md = "`![a](x.png)`\n\n```\n![b](y.png)\n```\n\n[not an image](z.png)\n"
    assert find_images(md) == []


def test_find_images_handles_brackets_in_alt_text():
    assert find_images("![E_{x~p}[f(x)]](fig.png)\n") == ["fig.png"]


def test_is_external():
    for src in ["http://a/x.png", "HTTPS://a/x.png", "//cdn/x.png", "data:image/png;base64,AA"]:
        assert is_external(src)
    for src in ["figures/x.png", "./x.png", "../x.png", "/abs/x.png"]:
        assert not is_external(src)


def test_image_types():
    assert IMAGE_TYPES[".png"] == "image/png"
    assert IMAGE_TYPES[".jpeg"] == "image/jpeg"
    assert IMAGE_TYPES[".svg"] == "image/svg+xml"


def test_local_images_resolve_against_base_dir(tmp_path):
    md = "![a](figures/x.png) ![b](https://h/y.png) ![c](./z.png)\n"
    images = local_images(md, tmp_path)
    assert [i.src for i in images] == ["figures/x.png", "./z.png"]
    assert images[0].path == (tmp_path / "figures" / "x.png").resolve()
    assert images[1].path == (tmp_path / "z.png").resolve()


def test_local_images_percent_decode(tmp_path):
    images = local_images("![a](<figures/my slide.png>)\n", tmp_path)
    assert images[0].path == (tmp_path / "figures" / "my slide.png").resolve()


def test_mime_is_case_insensitive(tmp_path):
    images = local_images("![a](X.PNG) ![b](y.bmp)\n", tmp_path)
    assert images[0].mime == "image/png"
    assert images[1].mime is None


def test_missing_images_lists_missing_and_unsupported_in_order(tmp_path, png):
    png(tmp_path / "figures" / "ok.png")
    (tmp_path / "old.bmp").write_bytes(b"BM")
    md = "![a](figures/gone.png) ![b](figures/ok.png) ![c](old.bmp) ![d](also-gone.jpg)\n"
    assert missing_images(local_images(md, tmp_path)) == [
        "figures/gone.png",
        "old.bmp",
        "also-gone.jpg",
    ]


def test_directory_named_like_an_image_is_missing(tmp_path):
    (tmp_path / "dir.png").mkdir()
    assert missing_images(local_images("![a](dir.png)\n", tmp_path)) == ["dir.png"]
