### Task 5: The export command and CLI

**Files:**
- Modify: `src/lecnotes/commands.py` (add `export` and `_export_source`)
- Modify: `src/lecnotes/cli.py` (add the `export` subparser, dispatch, `_report_export`)
- Test: `tests/test_export.py` (new), `tests/test_cli.py` (modify)

**Interfaces:**
- Consumes: `markdown_doc.local_images`, `markdown_doc.missing_images`, `export_html.render_html`, `export_notion.images_outside`, `export_notion.write_notion_zip`, `workdir.is_workdir`, `workdir.load_manifest`, `workdir.out_dir`, `workdir.notes_path`, `commands.prep`, `commands.finish`, `png` fixture, `synth` fixture
- Produces: `commands.export(target: Path, fmt: str, out: Path | None = None) -> dict` returning `{"ok": True, "format", "source", "output", "images", "bytes"}`; CLI `lecnotes export <source> --to {html,notion} [-o OUT] [--json]`

- [ ] **Step 1: Write the failing command tests**

Create `tests/test_export.py`:

```python
import zipfile

import pytest

from lecnotes import workdir
from lecnotes.commands import export, finish, prep
from lecnotes.errors import LecnotesError


@pytest.fixture
def finished(synth, tmp_path):
    """A prepped and finished 3-slide workdir with one figure."""
    pdf = synth(tmp_path / "lec1.pdf", [{"text": f"S{i}", "small_box": (100, 100, 300, 220)}
                                        for i in range(1, 4)])
    prep(pdf)
    root = tmp_path / "lec1.notes"
    workdir.notes_path(root).write_text(
        "# Lecture One\n\nWrapped\nprose.\n\n![node](figures/slide-002.png)\n", encoding="utf-8"
    )
    finish(root)
    return root


def test_html_from_workdir(finished):
    result = export(finished, "html")
    out = workdir.out_dir(finished) / "lec1.html"
    assert result == {
        "ok": True,
        "format": "html",
        "source": str(workdir.out_dir(finished) / "lec1.md"),
        "output": str(out),
        "images": 1,
        "bytes": out.stat().st_size,
    }
    html = out.read_text(encoding="utf-8")
    assert "data:image/png;base64," in html and "<title>Lecture One</title>" in html


def test_notion_from_workdir(finished):
    result = export(finished, "notion")
    out = workdir.out_dir(finished) / "lec1-notion.zip"
    assert result["output"] == str(out) and result["images"] == 1
    with zipfile.ZipFile(out) as zf:
        assert sorted(zf.namelist()) == ["Lecture One.md", "figures/slide-002.png"]


def test_markdown_file_directly(tmp_path, png):
    png(tmp_path / "img" / "a.png")
    md = tmp_path / "edited.md"
    md.write_text("# E\n\n![a](img/a.png)\n", encoding="utf-8")
    result = export(md, "html")
    assert result["output"] == str(tmp_path / "edited.html")
    assert result["source"] == str(md)


def test_out_option_and_overwrite(tmp_path):
    md = tmp_path / "n.md"
    md.write_text("text\n", encoding="utf-8")
    dest = tmp_path / "deep" / "dir" / "custom.html"
    export(md, "html", out=dest)
    first = dest.read_text()
    md.write_text("changed\n", encoding="utf-8")
    export(md, "html", out=dest)
    assert dest.read_text() != first


def test_source_not_found(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path / "nope.md", "html")
    assert exc.value.code == "source_not_found"


@pytest.mark.parametrize("name", ["notes.txt", "deck.pdf"])
def test_non_markdown_file_is_unsupported(tmp_path, name):
    (tmp_path / name).write_text("x")
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path / name, "html")
    assert exc.value.code == "unsupported_format"


def test_plain_directory_is_unsupported(tmp_path):
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path, "html")
    assert exc.value.code == "unsupported_format"


def test_workdir_before_finish(synth, tmp_path):
    prep(synth(tmp_path / "lec1.pdf", [{"text": "a"}]))
    with pytest.raises(LecnotesError) as exc:
        export(tmp_path / "lec1.notes", "html")
    assert exc.value.code == "not_finished"
    assert "finish" in exc.value.message


def test_workdir_with_notes_edited_after_finish(finished):
    workdir.notes_path(finished).write_text("# Lecture One\n\nnewer\n", encoding="utf-8")
    with pytest.raises(LecnotesError) as exc:
        export(finished, "notion")
    assert exc.value.code == "not_finished"
    assert "NOTES.md" in exc.value.message
    assert not (workdir.out_dir(finished) / "lec1-notion.zip").exists()


def test_missing_images_all_listed_nothing_written(tmp_path, png):
    png(tmp_path / "ok.png")
    md = tmp_path / "n.md"
    md.write_text("![a](gone1.png) ![b](ok.png) ![c](gone2.png) ![d](gone1.png)\n")
    with pytest.raises(LecnotesError) as exc:
        export(md, "html")
    assert exc.value.code == "image_not_found"
    assert exc.value.detail["missing"] == ["gone1.png", "gone2.png"]
    assert not (tmp_path / "n.html").exists()


def test_outside_root_rejected_for_notion_only(tmp_path, png):
    png(tmp_path / "shared" / "x.png")
    notes = tmp_path / "notes"
    notes.mkdir()
    md = notes / "n.md"
    md.write_text("![x](../shared/x.png)\n")

    with pytest.raises(LecnotesError) as exc:
        export(md, "notion")
    assert exc.value.code == "image_outside_root"
    assert exc.value.detail["outside"] == ["../shared/x.png"]
    assert not (notes / "n-notion.zip").exists()

    assert export(md, "html")["images"] == 1


def test_exporters_never_modify_the_markdown(finished):
    md = workdir.out_dir(finished) / "lec1.md"
    before = md.read_bytes()
    export(finished, "html")
    export(finished, "notion")
    assert md.read_bytes() == before
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_export.py -v`
Expected: FAIL with `ImportError: cannot import name 'export'`

- [ ] **Step 3: Implement `commands.export`**

Add to the imports at the top of `src/lecnotes/commands.py`:

```python
from .export_html import render_html
from .export_notion import images_outside, write_notion_zip
from .markdown_doc import local_images, missing_images
```

Append to `src/lecnotes/commands.py`:

```python
def _export_source(target: Path) -> Path:
    """The Markdown file to export, from a workdir or a .md path."""
    if not target.exists():
        raise LecnotesError(
            "source_not_found", f"no such file or directory: {target}", path=str(target)
        )

    if target.is_dir():
        if not workdir.is_workdir(target):
            raise LecnotesError(
                "unsupported_format",
                f"{target} is a directory but not a lecnotes workdir; "
                "pass a workdir or a .md file",
                path=str(target),
            )
        deck = workdir.load_manifest(target)["deck"]
        markdown = workdir.out_dir(target) / f"{deck}.md"
        if not markdown.is_file():
            raise LecnotesError(
                "not_finished",
                f"{markdown} does not exist yet; run `lecnotes finish` on this workdir first",
                path=str(target),
            )
        notes = workdir.notes_path(target)
        if notes.is_file() and notes.read_text(encoding="utf-8") != markdown.read_text(
            encoding="utf-8"
        ):
            raise LecnotesError(
                "not_finished",
                "NOTES.md has changed since the last finish; "
                "run `lecnotes finish` again before exporting",
                path=str(target),
            )
        return markdown

    if target.suffix.lower() != ".md":
        raise LecnotesError(
            "unsupported_format",
            f"cannot export {target.name}; pass a lecnotes workdir or a .md file",
            path=str(target),
        )
    return target


def export(target: Path, fmt: str, out: Path | None = None) -> dict:
    source = _export_source(Path(target))
    markdown = source.read_text(encoding="utf-8")
    base_dir = source.parent
    images = local_images(markdown, base_dir)

    # Validate everything before writing anything.
    missing = missing_images(images)
    if missing:
        raise LecnotesError(
            "image_not_found",
            "these images are missing or not a supported type "
            "(png, jpg, jpeg, gif, svg, webp): " + ", ".join(missing),
            missing=missing,
        )

    if fmt == "notion":
        outside = images_outside(images, base_dir)
        if outside:
            raise LecnotesError(
                "image_outside_root",
                "a Notion zip can only include images inside the Markdown file's "
                "folder; move or copy these: " + ", ".join(outside),
                outside=outside,
            )
        dest = Path(out) if out else base_dir / f"{source.stem}-notion.zip"
        write_notion_zip(markdown, images, base_dir, dest, source.stem)
    elif fmt == "html":
        dest = Path(out) if out else base_dir / f"{source.stem}.html"
        html = render_html(markdown, base_dir, source.stem)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
    else:
        raise ValueError(f"unknown export format: {fmt}")

    return {
        "ok": True,
        "format": fmt,
        "source": str(source),
        "output": str(dest),
        "images": len({image.path for image in images}),
        "bytes": dest.stat().st_size,
    }
```

- [ ] **Step 4: Run command tests**

Run: `uv run pytest tests/test_export.py -v` → PASS.
Run: `uv run pytest tests/test_cli.py -v` → `test_every_raised_error_code_has_a_cli_scenario` now FAILS (three new codes have no scenario). That is expected and fixed in Step 5.

- [ ] **Step 5: Write the failing CLI tests**

In `tests/test_cli.py`, add after the `_figure_malformed` scenario function:

```python
def _finished(synth, tmp_path, notes="# T\n\n![a](figures/slide-001.png)\n"):
    pdf, root = _prepped(synth, tmp_path, notes=notes)
    commands.finish(root)
    return root


def _not_finished(tmp_path, synth, monkeypatch):
    _, root = _prepped(synth, tmp_path)
    return ["export", str(root), "--to", "html"]


def _image_not_found(tmp_path, synth, monkeypatch):
    md = tmp_path / "notes.md"
    md.write_text("![x](figures/missing.png)\n")
    return ["export", str(md), "--to", "html"]


def _image_outside_root(tmp_path, synth, monkeypatch):
    from conftest import make_png

    make_png(tmp_path / "shared" / "x.png")
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "n.md").write_text("![x](../shared/x.png)\n")
    return ["export", str(notes / "n.md"), "--to", "notion"]
```

Add three entries to `ERROR_SCENARIOS`:

```python
    "not_finished": (_not_finished, 1),
    "image_not_found": (_image_not_found, 1),
    "image_outside_root": (_image_outside_root, 1),
```

Add these tests (anywhere after the fixtures):

```python
def test_export_html_human_output(synth, tmp_path, capsys):
    root = _finished(synth, tmp_path)
    capsys.readouterr()
    assert main(["export", str(root), "--to", "html"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == str(root / "out" / "lec1.html")
    assert "1 image" in out


def test_export_notion_json(synth, tmp_path, capsys):
    root = _finished(synth, tmp_path)
    capsys.readouterr()
    assert main(["export", str(root), "--to", "notion", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["format"] == "notion"
    assert payload["output"].endswith("lec1-notion.zip")
    assert payload["images"] == 1 and payload["bytes"] > 0


def test_export_requires_to(tmp_path, capsys):
    md = tmp_path / "n.md"
    md.write_text("x\n")
    assert main(["export", str(md)]) == 1
    assert "--to" in capsys.readouterr().err


def test_export_rejects_unknown_format(tmp_path, capsys):
    md = tmp_path / "n.md"
    md.write_text("x\n")
    assert main(["export", str(md), "--to", "pdf"]) == 1
```

If `from conftest import make_png` does not import under this project's pytest configuration, request the `png` fixture instead by changing the scenario signature is not possible (scenarios share one signature) — so in that case add `import pymupdf` at the top of `test_cli.py` and build the PNG inline exactly as `make_png` does.

- [ ] **Step 6: Run to verify failure**

Run: `uv run pytest tests/test_cli.py -v`
Expected: the new export tests and the three new parametrized scenarios FAIL (`invalid choice: 'export'`).

- [ ] **Step 7: Implement the CLI**

In `src/lecnotes/cli.py`, import `export` alongside `prep` and `finish` (`from .commands import export, finish, prep`). In `_build_parser`, after the `finish` subparser:

```python
    e = sub.add_parser("export", help="convert finished notes to HTML or a Notion import zip")
    e.add_argument("source", type=Path, help="a finished workdir, or any .md file")
    e.add_argument(
        "--to", dest="fmt", required=True, choices=["html", "notion"], help="output format"
    )
    e.add_argument("-o", "--out", type=Path, default=None, help="output file path")
    e.add_argument("--json", action="store_true", help="machine-readable output")
```

Add the reporter next to the others:

```python
def _report_export(result: dict) -> None:
    size = result["bytes"]
    human = f"{size / 1_048_576:.1f} MB" if size >= 1_048_576 else f"{size / 1024:.0f} KB"
    noun = "image" if result["images"] == 1 else "images"
    print(f"{result['output']}")
    print(f"  {result['images']} {noun}, {human}")
```

In `main`, replace the `if/else` dispatch with:

```python
        if args.command == "prep":
            result = prep(args.source, out=args.out, force=args.force)
            reporter = _report_prep
        elif args.command == "finish":
            result = finish(args.workdir)
            reporter = _report_finish
        else:
            result = export(args.source, args.fmt, out=args.out)
            reporter = _report_export
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py tests/test_export.py -v` → PASS. Then `uv run pytest -q` → all pass, no warnings.

- [ ] **Step 9: Commit**

```bash
git add src/lecnotes/commands.py src/lecnotes/cli.py tests/test_export.py tests/test_cli.py
git commit -m "Add lecnotes export --to html|notion"
```

---

