# Task 3 report: Vendor KaTeX

## What I implemented

Followed `task-3-brief.md` exactly.

1. **Fetched and verified KaTeX 0.18.7** from the npm registry tarball (`https://registry.npmjs.org/katex/-/katex-0.18.7.tgz`), checked its sha512 integrity against the value published in `https://registry.npmjs.org/katex/0.18.7` (`meta.json`'s `dist.integrity`). The digest matched — `integrity ok sha512`.
2. **Vendored** into `src/lecnotes/vendor/katex/`:
   - `katex.min.js` — 272,715 bytes, contains no `</script` and no `<!--` (verified with grep before writing tests).
   - `katex.min.css` — 20 `@font-face` rules, each with `src:url(fonts/KaTeX_X.woff2) format("woff2"),url(fonts/KaTeX_X.woff) format("woff"),url(fonts/KaTeX_X.ttf) format("truetype")`.
   - `LICENSE` — MIT, Khan Academy and contributors.
   - `VERSION` — `0.18.7\n`.
   - `fonts/*.woff2` — 20 files, exactly the KaTeX_AMS/Caligraphic/Fraktur/Main/Math/SansSerif/Script/Size1-4/Typewriter set.
   - `src/lecnotes/vendor/__init__.py` and `src/lecnotes/vendor/katex/__init__.py` — both empty, making these regular packages so `importlib.resources.files()` can address them.
3. **`src/lecnotes/katex.py`** — `KATEX_VERSION = "0.18.7"`; `katex_css()` reads the vendored CSS and replaces each `@font-face`'s three-source `src:` (woff2/woff/ttf) with a single `src:url(data:font/woff2;base64,<...>) format("woff2")`, inlining the corresponding vendored `.woff2` file; `katex_js()` reads the vendored JS as-is. Both are `@lru_cache(maxsize=1)`, satisfying the "cached" interface requirement (identity-equal on repeat calls).
4. **`tests/test_katex.py`** — the six tests specified in the brief verbatim, covering: version matches vendored file; every `@font-face` inlines to exactly one `url(...)` which is a base64 woff2 data URI (and no `fonts/`, `.woff)`, `.ttf)` remnants); `.katex{` rules survive; the JS is script-tag-safe (no `</script`, no `<!--`); both accessors are cached (`is` identity); the LICENSE contains "MIT".

## TDD evidence

**RED**

```
$ uv run pytest tests/test_katex.py -v
...
ImportError while importing test module '.../tests/test_katex.py'.
tests/test_katex.py:4: in <module>
    from lecnotes.katex import KATEX_VERSION, katex_css, katex_js
E   ModuleNotFoundError: No module named 'lecnotes.katex'
=========================== short test summary info ============================
ERROR tests/test_katex.py
```

Expected: `lecnotes/katex.py` did not exist yet, so importing it fails with `ModuleNotFoundError`, exactly as the brief predicted.

**GREEN**

```
$ uv run pytest tests/test_katex.py -v
tests/test_katex.py::test_version_matches_vendored_file PASSED           [ 16%]
tests/test_katex.py::test_every_font_face_is_an_inlined_woff2 PASSED     [ 33%]
tests/test_katex.py::test_css_keeps_katex_rules PASSED                   [ 50%]
tests/test_katex.py::test_js_is_safe_to_inline_in_a_script_tag PASSED    [ 66%]
tests/test_katex.py::test_assets_are_cached PASSED                      [ 83%]
tests/test_katex.py::test_license_is_vendored PASSED                    [100%]
============================== 6 passed in 0.01s ===============================
```

**Full suite**

```
$ uv run pytest -q
308 passed in 5.02s
```

Before this task: 302 passed. After: 308 passed (302 + 6 new `test_katex.py` tests). No warnings.

**Packaging check**

```
$ uv build --wheel -o "$SCRATCH/wheel"
Successfully built .../lecnotes-0.1.0-py3-none-any.whl
$ unzip -l "$SCRATCH/wheel"/*.whl | grep -c 'vendor/katex/fonts/.*woff2'
20
```

The wheel also ships `lecnotes/vendor/__init__.py`, `lecnotes/vendor/katex/__init__.py`, `LICENSE`, `VERSION`, `katex.min.css`, and `katex.min.js` (confirmed via `unzip -l`), so `hatchling`'s `packages = ["src/lecnotes"]` picks up the whole vendor tree with no extra config needed — `vendor` and `vendor/katex` are regular Python packages (they have `__init__.py`), and hatchling's default wheel builder includes all files under an included package directory, data files included.

## Files changed

- `src/lecnotes/vendor/__init__.py` (new, empty)
- `src/lecnotes/vendor/katex/__init__.py` (new, empty)
- `src/lecnotes/vendor/katex/katex.min.js` (new, vendored, 272,715 bytes)
- `src/lecnotes/vendor/katex/katex.min.css` (new, vendored)
- `src/lecnotes/vendor/katex/LICENSE` (new, vendored, MIT)
- `src/lecnotes/vendor/katex/VERSION` (new, `0.18.7`)
- `src/lecnotes/vendor/katex/fonts/*.woff2` (new, 20 files, vendored)
- `src/lecnotes/katex.py` (new)
- `tests/test_katex.py` (new)

## Deviations from the brief

None. The brief's exact code for `tests/test_katex.py` and `src/lecnotes/katex.py` was used verbatim, and the vendored file shapes matched the controller's pre-inspection precisely (272,715-byte JS with no `</script`/`<!--`; 20 `@font-face` rules each with the three-format `src:` list).

## Self-review findings

- Read the diff: only the specified files were added (`git status --short` after staging showed exactly `src/lecnotes/katex.py`, `src/lecnotes/vendor/**`, `tests/test_katex.py`; nothing under `docs/` was staged).
- `__pycache__` directories created by running pytest under `src/lecnotes/vendor/` are gitignored (`__pycache__/` in `.gitignore`) and were not staged.
- No runtime dependency was added — `katex.py` uses only the stdlib (`base64`, `re`, `functools.lru_cache`, `importlib.resources`), matching the global constraint that KaTeX is vendored files, not a package dependency.
- Confirmed no other module imports `lecnotes.katex` yet (Task 4 will wire it into `export_html.py`), so this task is self-contained and doesn't touch behavior of any existing code path.

## Concerns

None. Task complete and self-contained; ready for Task 4 (HTML export) to consume `katex_css()`/`katex_js()`.
