### Task 2: Image links and where they point

**Files:**
- Create: `src/lecnotes/markdown_doc.py`
- Modify: `tests/conftest.py` (add `make_png` and the `png` fixture)
- Test: `tests/test_markdown_doc.py`

**Interfaces:**
- Consumes: `mdparse.inline_tokens`
- Produces:
  - `IMAGE_TYPES: dict[str, str]` — lowercase extension → MIME type (see Global Constraints)
  - `find_images(markdown: str) -> list[str]` — `src` of every image token, document order, de-duplicated, empty srcs dropped
  - `is_external(src: str) -> bool` — True for `http://`, `https://`, `//`, `data:` (case-insensitive)
  - `LocalImage` — frozen dataclass: `src: str` (as written), `path: Path` (absolute, resolved); property `mime -> str | None`
  - `local_images(markdown: str, base_dir: Path) -> list[LocalImage]` — non-external images, `src` percent-decoded and resolved against `base_dir`
  - `missing_images(images: list[LocalImage]) -> list[str]` — `src` of each image that is not an existing file or has an unsupported extension, in the given order
  - `tests/conftest.py`: `make_png(path, width=4, height=3) -> Path` and fixture `png` returning `make_png`

- [ ] **Step 1: Add the PNG helper to conftest**

Append to `tests/conftest.py`:

```python
def make_png(path, width=4, height=3) -> Path:
    """A tiny real PNG, so image tests never need checked-in binaries."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), False)
    pix.clear_with(200)
    pix.save(path)
    return path


@pytest.fixture
def png():
    return make_png
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_markdown_doc.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_markdown_doc.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lecnotes.markdown_doc'`

- [ ] **Step 4: Implement**

Create `src/lecnotes/markdown_doc.py`:

```python
"""Image links in a Markdown document, and where they point on disk.

Returns findings only. Deciding which findings are errors is commands.py's job.
"""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from .mdparse import inline_tokens

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}

_EXTERNAL_PREFIXES = ("http://", "https://", "//", "data:")


def find_images(markdown: str) -> list[str]:
    """Every image src, in document order, de-duplicated."""
    seen: dict[str, None] = {}
    for token in inline_tokens(markdown):
        if token.type == "image":
            src = token.attrGet("src") or ""
            if src:
                seen.setdefault(src, None)
    return list(seen)


def is_external(src: str) -> bool:
    """Remote or inline images: never fetched, never packaged, left as written."""
    return src.lower().startswith(_EXTERNAL_PREFIXES)


@dataclass(frozen=True)
class LocalImage:
    src: str  # as it appears in the parsed Markdown
    path: Path  # absolute and resolved

    @property
    def mime(self) -> str | None:
        return IMAGE_TYPES.get(self.path.suffix.lower())


def local_images(markdown: str, base_dir: Path) -> list[LocalImage]:
    base = Path(base_dir).resolve()
    return [
        # markdown-it percent-encodes link targets; the file on disk is not encoded.
        LocalImage(src=src, path=(base / unquote(src)).resolve())
        for src in find_images(markdown)
        if not is_external(src)
    ]


def missing_images(images: list[LocalImage]) -> list[str]:
    """Srcs that are not an existing file of a supported image type."""
    return [image.src for image in images if image.mime is None or not image.path.is_file()]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_markdown_doc.py -v` → PASS. Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 6: Commit**

```bash
git add src/lecnotes/markdown_doc.py tests/test_markdown_doc.py tests/conftest.py
git commit -m "Find image links in Markdown and resolve them on disk"
```

---

