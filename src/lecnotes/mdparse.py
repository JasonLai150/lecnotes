"""The one Markdown parser configuration.

finish's figure validation and both exporters parse with this, so they can never
disagree about what counts as an image link.
"""

from collections.abc import Iterator

from markdown_it import MarkdownIt
from markdown_it.token import Token


def new_parser() -> MarkdownIt:
    """A fresh parser. Take one whenever you need to add render rules."""
    return MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])


# Shared for parsing only. Adding render rules to it would leak into every caller.
PARSER = new_parser()


def inline_tokens(markdown: str, parser: MarkdownIt = PARSER) -> Iterator[Token]:
    """Every inline child token (text, image, link_open, ...) in document order.

    Code spans, fenced code and indented code never produce image, link, or text
    children, so example links inside code are invisible here.
    """
    for block in parser.parse(markdown):
        if block.type == "inline" and block.children:
            yield from block.children
