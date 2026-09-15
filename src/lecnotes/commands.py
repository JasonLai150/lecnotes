"""Orchestration for the two verbs. Returns plain dicts; cli.py does the shaping."""

import shutil
import tempfile
from pathlib import Path

from . import workdir
from .errors import LecnotesError
from .figures import TARGET_LONG_EDGE
from .ingest import resolve_source
from .instructions import render_instructions
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
        shutil.copyfile(info.pdf, workdir.source_path(root))

    manifest = {
        "deck": info.deck,
        "source": info.source_name,
        "source_format": info.source_format,
        "converted": info.converted,
        "slides": len(rows),
        "figures": sum(r["figure"] for r in rows),
        "rendered_long_edge": TARGET_LONG_EDGE,
        "pages": rows,
    }
    workdir.save_manifest(root, manifest)

    workdir.instructions_path(root).write_text(
        render_instructions(
            deck=info.deck,
            slides=manifest["slides"],
            figures=manifest["figures"],
            source_name=info.source_name,
            workdir_name=root.name,
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
        "figures": manifest["figures"],
        "notes_preserved": preserved,
        "instructions": str(workdir.instructions_path(root)),
        "write_to": str(notes),
        "next": f"lecnotes finish {root}",
    }
