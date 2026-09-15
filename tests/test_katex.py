import re
from importlib.resources import files

from lecnotes.katex import KATEX_VERSION, katex_css, katex_js


def test_version_matches_vendored_file():
    vendored = files("lecnotes.vendor.katex").joinpath("VERSION").read_text().strip()
    assert KATEX_VERSION == vendored == "0.18.7"


def test_every_font_face_is_an_inlined_woff2():
    css = katex_css()
    faces = re.findall(r"@font-face\{[^}]*\}", css)
    assert len(faces) == 20
    for face in faces:
        assert 'src:url(data:font/woff2;base64,' in face
        assert face.count("url(") == 1
    assert "url(fonts/" not in css
    assert ".woff)" not in css and ".ttf)" not in css


def test_css_keeps_katex_rules():
    assert ".katex{" in katex_css() or ".katex {" in katex_css()


def test_js_is_safe_to_inline_in_a_script_tag():
    js = katex_js()
    assert "katex" in js
    assert "</script" not in js.lower()
    assert "<!--" not in js


def test_assets_are_cached():
    assert katex_css() is katex_css()
    assert katex_js() is katex_js()


def test_license_is_vendored():
    assert "MIT" in files("lecnotes.vendor.katex").joinpath("LICENSE").read_text()
