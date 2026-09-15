"""Argument parsing, output shaping, exit codes. Nothing else lives here."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .commands import export, finish, prep
from .errors import LecnotesError


class _UsageError(Exception):
    """Raised by _ArgumentParser.error() in place of argparse's default sys.exit(2).

    A missing positional or an unrecognized subcommand is a usage error, so it
    must map to exit code 1 like every other usage/validation failure -- not
    the SystemExit(2) argparse raises for every parsing error by default.
    """


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise _UsageError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="lecnotes",
        description="Turn a lecture deck into a workdir an agent can write notes from.",
    )
    parser.add_argument("--version", action="version", version=f"lecnotes {__version__}")
    sub = parser.add_subparsers(dest="command", parser_class=_ArgumentParser)

    p = sub.add_parser("prep", help="render a deck into a new workdir")
    p.add_argument("source", type=Path, help="deck to prepare (.pdf, .pptx, .ppt)")
    p.add_argument("-o", "--out", type=Path, default=None, help="workdir path")
    p.add_argument("--force", action="store_true", help="re-render an existing workdir")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    f = sub.add_parser("finish", help="validate figure links and assemble the document")
    f.add_argument("workdir", type=Path, help="workdir created by prep")
    f.add_argument("--json", action="store_true", help="machine-readable output")

    e = sub.add_parser("export", help="convert finished notes to HTML or a Notion import zip")
    e.add_argument("source", type=Path, help="a finished workdir, or any .md file")
    e.add_argument(
        "--to", dest="fmt", required=True, choices=["html", "notion"], help="output format"
    )
    e.add_argument("-o", "--out", type=Path, default=None, help="output file path")
    e.add_argument("--json", action="store_true", help="machine-readable output")

    return parser


def _report_prep(result: dict) -> None:
    print(f"{result['workdir']}")
    print(f"  {result['slides']} slides")
    if result["notes_preserved"]:
        print("  NOTES.md preserved (not overwritten)")
    print(f"  read  {result['instructions']}")
    print(f"  write {result['write_to']}")
    print(f"  then  {result['next']}")


def _report_finish(result: dict) -> None:
    print(f"{result['output']}")
    print(f"  {result['figures_resolved']} figures resolved")


def _report_export(result: dict) -> None:
    size = result["bytes"]
    human = f"{size / 1_048_576:.1f} MB" if size >= 1_048_576 else f"{size / 1024:.0f} KB"
    noun = "image" if result["images"] == 1 else "images"
    print(f"{result['output']}")
    print(f"  {result['images']} {noun}, {human}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except _UsageError:
        # error() already printed usage + message to stderr.
        return 1

    if args.command is None:
        parser.print_usage(sys.stderr)
        return 1

    try:
        if args.command == "prep":
            result = prep(args.source, out=args.out, force=args.force)
            reporter = _report_prep
        elif args.command == "finish":
            result = finish(args.workdir)
            reporter = _report_finish
        else:
            result = export(args.source, args.fmt, out=args.out)
            reporter = _report_export
    except LecnotesError as err:
        # One place renders every failure, so --json and human output cannot drift.
        if args.json:
            print(json.dumps(err.to_dict()))
        else:
            print(f"error: {err.message}", file=sys.stderr)
        return err.exit_code
    except Exception as err:
        # A --json caller parses stdout; a bare traceback would leave it empty.
        # Humans get the traceback, which is more useful to them than a summary.
        if not args.json:
            raise
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "internal_error",
                    "message": f"{type(err).__name__}: {err}",
                }
            )
        )
        return 1

    if args.json:
        print(json.dumps(result))
    else:
        reporter(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
