### Task 3: Vendor KaTeX

**Files:**
- Create: `src/lecnotes/vendor/__init__.py`, `src/lecnotes/vendor/katex/__init__.py` (both empty)
- Create: `src/lecnotes/vendor/katex/{katex.min.js,katex.min.css,LICENSE,VERSION,fonts/*.woff2}`
- Create: `src/lecnotes/katex.py`
- Test: `tests/test_katex.py`

**Interfaces:**
- Produces: `KATEX_VERSION = "0.18.7"`; `katex_css() -> str` (KaTeX CSS with every `@font-face` `src` a single WOFF2 data URI; cached); `katex_js() -> str` (cached)

- [ ] **Step 1: Fetch and verify KaTeX 0.18.7**

```bash
SCRATCH=/private/tmp/claude-501/-Users-jasonlai150-Documents-GitHub-4440/b8ce7be5-28b5-4a05-868b-6c0cf5495ca3/scratchpad
rm -rf "$SCRATCH/katex-vendor" && mkdir -p "$SCRATCH/katex-vendor" && cd "$SCRATCH/katex-vendor"
curl -sL https://registry.npmjs.org/katex/0.18.7 -o meta.json
curl -sL https://registry.npmjs.org/katex/-/katex-0.18.7.tgz -o katex.tgz
python3 - <<'EOF'
import base64, hashlib, json
meta = json.load(open("meta.json"))
algo, digest = meta["dist"]["integrity"].split("-", 1)
actual = base64.b64encode(hashlib.new(algo, open("katex.tgz", "rb").read()).digest()).decode()
assert actual == digest, "integrity mismatch"
print("integrity ok", algo)
EOF
tar -xzf katex.tgz
DEST=/Users/jasonlai150/Documents/GitHub/lecnotes/src/lecnotes/vendor/katex
mkdir -p "$DEST/fonts"
cp package/dist/katex.min.js package/dist/katex.min.css package/LICENSE "$DEST/"
cp package/dist/fonts/*.woff2 "$DEST/fonts/"
printf '0.18.7\n' > "$DEST/VERSION"
ls "$DEST/fonts" | wc -l   # expect 20
```

Stop and report BLOCKED if the integrity check fails.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_katex.py`:

```python
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
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_katex.py -v` → FAIL (`ModuleNotFoundError: lecnotes.katex`).

- [ ] **Step 4: Implement**

Create `src/lecnotes/katex.py`:

```python
"""The vendored KaTeX renderer, prepared for inlining into one HTML file."""

import base64
import re
from functools import lru_cache
from importlib.resources import files

KATEX_VERSION = "0.18.7"

# Each @font-face lists woff2, woff and ttf. Keep only woff2 (every current browser
# reads it), inlined, so the page never asks for a file.
_FONT_SOURCES = re.compile(
    r'src:url\(fonts/(KaTeX_[A-Za-z0-9_-]+)\.woff2\) format\("woff2"\)[^;}]*'
)


def _root():
    return files("lecnotes.vendor.katex")


@lru_cache(maxsize=1)
def katex_css() -> str:
    css = _root().joinpath("katex.min.css").read_text(encoding="utf-8")

    def inline(match: re.Match) -> str:
        data = _root().joinpath("fonts", f"{match.group(1)}.woff2").read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        return f'src:url(data:font/woff2;base64,{encoded}) format("woff2")'

    return _FONT_SOURCES.sub(inline, css)


@lru_cache(maxsize=1)
def katex_js() -> str:
    return _root().joinpath("katex.min.js").read_text(encoding="utf-8")
```

- [ ] **Step 5: Run tests and confirm packaging**

Run: `uv run pytest tests/test_katex.py -v` → PASS. Then `uv run pytest -q` → all pass, no warnings.
Run: `uv build --wheel -o "$SCRATCH/wheel" && unzip -l "$SCRATCH/wheel"/*.whl | grep -c 'vendor/katex/fonts/.*woff2'` → `20`.

- [ ] **Step 6: Commit**

```bash
git add src/lecnotes/vendor src/lecnotes/katex.py tests/test_katex.py
```
Subject: "Vendor KaTeX 0.18.7 for rendering math in HTML exports"

---

