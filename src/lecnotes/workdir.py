"""The one module that knows the workdir layout.

Both commands go through here, so path literals do not scatter across the
codebase.
"""

import json
from pathlib import Path

from .errors import LecnotesError

MANIFEST = "manifest.json"
SOURCE = "source.pdf"
PAGES = "pages"
NOTES = "NOTES.md"
INSTRUCTIONS = "INSTRUCTIONS.md"
OUT = "out"
OUT_FIGURES = "out/figures"


def manifest_path(root: Path) -> Path:
    return Path(root) / MANIFEST


def source_path(root: Path) -> Path:
    return Path(root) / SOURCE


def pages_dir(root: Path) -> Path:
    return Path(root) / PAGES


def notes_path(root: Path) -> Path:
    return Path(root) / NOTES


def instructions_path(root: Path) -> Path:
    return Path(root) / INSTRUCTIONS


def out_dir(root: Path) -> Path:
    return Path(root) / OUT


def out_figures_dir(root: Path) -> Path:
    return Path(root) / OUT / "figures"


def page_png(root: Path, n: int) -> Path:
    return pages_dir(root) / f"slide-{n:03d}.png"


def page_txt(root: Path, n: int) -> Path:
    return pages_dir(root) / f"slide-{n:03d}.txt"


def rel_png(n: int) -> str:
    return f"{PAGES}/slide-{n:03d}.png"


def rel_txt(n: int) -> str:
    return f"{PAGES}/slide-{n:03d}.txt"


def is_workdir(root: Path) -> bool:
    return manifest_path(root).is_file()


def require_workdir(root: Path) -> None:
    if not is_workdir(root):
        raise LecnotesError(
            "not_a_workdir",
            f"{root} is not a lecnotes workdir (no {MANIFEST})",
            path=str(root),
        )


def save_manifest(root: Path, data: dict) -> None:
    Path(root).mkdir(parents=True, exist_ok=True)
    manifest_path(root).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_manifest(root: Path) -> dict:
    return json.loads(manifest_path(root).read_text(encoding="utf-8"))
