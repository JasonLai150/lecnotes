"""Argument parsing, output shaping, exit codes. Nothing else lives here."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .commands import finish, prep
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

    return parser


def _report_prep(result: dict) -> None:
    print(f"{result['workdir']}")
    print(f"  {result['slides']} slides, {result['figures']} with figures")
    if result["notes_preserved"]:
        print("  NOTES.md preserved (not overwritten)")
    print(f"  read  {result['instructions']}")
    print(f"  write {result['write_to']}")
    print(f"  then  {result['next']}")


def _report_finish(result: dict) -> None:
    print(f"{result['output']}")
    print(f"  {result['figures_resolved']} figures resolved")


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
        else:
            result = finish(args.workdir)
            reporter = _report_finish
    except LecnotesError as err:
        # One place renders every failure, so --json and human output cannot drift.
        if args.json:
            print(json.dumps(err.to_dict()))
        else:
            print(f"error: {err.message}", file=sys.stderr)
        return err.exit_code

    if args.json:
        print(json.dumps(result))
    else:
        reporter(result)
    return 0
