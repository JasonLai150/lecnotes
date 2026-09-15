"""Orchestration for prep, finish and export. Returns plain dicts; cli.py does the shaping."""

import os
import shlex
import shutil
import tempfile
from pathlib import Path

from . import workdir
from .errors import LecnotesError
from .export_html import render_html
from .export_notion import images_outside, write_notion_zip
from .figures import TARGET_LONG_EDGE, crop_render, find_malformed, find_refs
from .ingest import resolve_source
from .instructions import render_instructions
from .markdown_doc import IMAGE_TYPES, local_images, missing_images
from .render import render_deck

NOTES_STUB = (
    "<!-- Replace this file with the notes. See INSTRUCTIONS.md. -->\n"
)


def prep(source: Path, out: Path | None = None, force: bool = False) -> dict:
    source = Path(source)

    with tempfile.TemporaryDirectory() as tmp:
        info = resolve_source(source, Path(tmp))
        root = Path(out) if out else source.parent / f"{info.deck}.notes"

        if root.exists() and not force:
            raise LecnotesError(
                "workdir_exists",
                f"{root} already exists; pass --force to re-render it "
                "(NOTES.md is preserved either way)",
                path=str(root),
            )
        # --force deletes pages/ below, so it only applies to something prep made.
        if root.exists() and force and not workdir.is_workdir(root):
            raise LecnotesError(
                "workdir_exists",
                f"{root} exists and is not a lecnotes workdir; refusing to overwrite it",
                path=str(root),
            )

        notes = workdir.notes_path(root)
        preserved = notes.is_file()

        # Drop stale pages so a shorter re-render cannot leave orphans behind.
        if workdir.pages_dir(root).exists():
            shutil.rmtree(workdir.pages_dir(root))

        rows = render_deck(info.pdf, root)
        dest = workdir.source_path(root)
        # Re-prepping from the workdir's own source.pdf: it is already in place.
        if not (dest.exists() and os.path.samefile(info.pdf, dest)):
            shutil.copyfile(info.pdf, dest)

    manifest = {
        "deck": info.deck,
        "source": info.source_name,
        "source_format": info.source_format,
        "converted": info.converted,
        "slides": len(rows),
        "rendered_long_edge": TARGET_LONG_EDGE,
        "pages": rows,
    }
    workdir.save_manifest(root, manifest)

    workdir.instructions_path(root).write_text(
        render_instructions(
            deck=info.deck,
            slides=manifest["slides"],
            source_name=info.source_name,
        ),
        encoding="utf-8",
    )

    if not preserved:
        notes.write_text(NOTES_STUB, encoding="utf-8")

    return {
        "ok": True,
        "workdir": str(root),
        "deck": info.deck,
        "slides": manifest["slides"],
        "notes_preserved": preserved,
        "instructions": str(workdir.instructions_path(root)),
        "write_to": str(notes),
        "next": f"lecnotes finish {shlex.quote(str(root))}",
    }


def finish(root: Path) -> dict:
    root = Path(root)
    workdir.require_workdir(root)

    manifest = workdir.load_manifest(root)
    notes = workdir.notes_path(root)
    body = notes.read_text(encoding="utf-8") if notes.is_file() else ""

    if body.strip() == NOTES_STUB.strip() or not body.strip():
        raise LecnotesError(
            "notes_empty",
            f"{notes} has not been written yet; see {workdir.INSTRUCTIONS}",
            path=str(notes),
        )

    slides = manifest["slides"]
    refs = find_refs(body)

    # Validate every reference before writing anything, so a bad link leaves no
    # half-built output behind. Malformed links are reported first: fixing their
    # form can change which slides they point at.
    malformed = find_malformed(body)
    if malformed:
        raise LecnotesError(
            "figure_malformed",
            "NOTES.md has slide image links not written as "
            "![caption](figures/slide-NNN.png): " + ", ".join(malformed) +
            ". Usual causes: an unbalanced [ or ] in the caption, a missing !, "
            "or a path other than figures/slide-NNN.png.",
            bad_links=malformed,
        )

    bad = [{"slide": n, "max": slides} for n in refs if not 1 <= n <= slides]
    if bad:
        raise LecnotesError(
            "figure_out_of_range",
            "NOTES.md references slides that are not in this deck: "
            + ", ".join(str(b["slide"]) for b in bad)
            + f" (deck has {slides})",
            bad_refs=bad,
        )

    figures_dir = workdir.out_figures_dir(root)
    if figures_dir.exists():
        shutil.rmtree(figures_dir)  # a rebuild must not leave last run's figures
    figures_dir.mkdir(parents=True, exist_ok=True)

    source = workdir.source_path(root)
    for n in refs:
        crop_render(source, n, figures_dir / f"slide-{n:03d}.png")

    out = workdir.out_dir(root) / f"{manifest['deck']}.md"
    out.write_text(body, encoding="utf-8")

    return {
        "ok": True,
        "workdir": str(root),
        "deck": manifest["deck"],
        "output": str(out),
        "figures_resolved": len(refs),
    }


def _export_source(target: Path) -> tuple[Path, Path | None]:
    """The Markdown file to export, and the workdir it came from (None for a .md path)."""
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
                f"NOTES.md and {markdown} differ. If NOTES.md is the version to keep, "
                "run `lecnotes finish` on this workdir first. If "
                f"out/{markdown.name} was edited on purpose, export it directly: "
                f"`lecnotes export {shlex.quote(str(markdown))} --to ...`",
                path=str(target),
            )
        return markdown, target

    if target.suffix.lower() != ".md":
        raise LecnotesError(
            "unsupported_format",
            f"cannot export {target.name}; pass a lecnotes workdir or a .md file",
            path=str(target),
        )
    return target, None


def _same_file(a: Path, b: Path) -> bool:
    return a.exists() and b.exists() and os.path.samefile(a, b)


def export(target: Path, fmt: str, out: Path | None = None) -> dict:
    source, root = _export_source(Path(target))
    markdown = source.read_text(encoding="utf-8")
    base_dir = source.parent
    images = local_images(markdown, base_dir)

    # Validate everything before writing anything.
    missing = missing_images(images)
    if missing:
        unsupported = [image.src for image in images if image.mime is None]
        groups = []
        absent = [src for src in missing if src not in unsupported]
        if absent:
            groups.append("missing: " + ", ".join(absent))
        if unsupported:
            types = ", ".join(ext.lstrip(".") for ext in IMAGE_TYPES)
            groups.append(f"unsupported type (use {types}): " + ", ".join(unsupported))
        raise LecnotesError(
            "image_not_found",
            "these images cannot be used: " + "; ".join(groups),
            missing=missing,
            unsupported=unsupported,
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
    elif fmt == "html":
        dest = Path(out) if out else base_dir / f"{source.stem}.html"
    else:
        raise ValueError(f"unknown export format: {fmt}")

    # By file identity, not path string: case-insensitive filesystems, hard links
    # and symlinks all give one file several names.
    if _same_file(dest, source):
        raise LecnotesError(
            "invalid_output",
            f"exporting to {dest} would overwrite the Markdown being exported; "
            "pass a different -o path",
            path=str(dest),
        )
    if root is not None and _same_file(dest, workdir.notes_path(root)):
        raise LecnotesError(
            "invalid_output",
            f"exporting to {dest} would overwrite this workdir's NOTES.md; "
            "pass a different -o path",
            path=str(dest),
        )
    if dest.is_dir():
        raise LecnotesError(
            "invalid_output",
            f"{dest} is a directory; -o must be a file path",
            path=str(dest),
        )
    # The nearest ancestor that exists is where mkdir would start; it must be a directory.
    ancestor = next(p for p in dest.absolute().parents if p.exists())
    if not ancestor.is_dir():
        raise LecnotesError(
            "invalid_output",
            f"{ancestor} is a file, not a directory; -o must be a path inside a directory",
            path=str(dest),
        )

    if fmt == "notion":
        write_notion_zip(markdown, images, base_dir, dest, source.stem)
    else:
        html = render_html(markdown, base_dir, source.stem)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")

    return {
        "ok": True,
        "format": fmt,
        "source": str(source),
        "output": str(dest),
        "images": len({image.path for image in images}),
        "bytes": dest.stat().st_size,
    }
