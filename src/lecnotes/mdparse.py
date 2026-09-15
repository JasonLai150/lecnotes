"""The one Markdown parser configuration.

finish's figure validation and both exporters parse with this, so they can never
disagree about what counts as an image link.
"""

import re
from collections.abc import Iterator

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from mdit_py_plugins.dollarmath import dollarmath_plugin

_MATH_INLINE = ("math_inline", "math_inline_double")

# One blockquote marker: up to 3 leading spaces, ">", then at most one space.
_BLOCKQUOTE_MARKER = re.compile(r"^[ ]{0,3}>[ ]?")


def _strip_blockquote_markers(state: StateCore) -> None:
    """Undo a dollarmath quirk: inside a blockquote, ``$$...$$`` keeps the ">"
    markers in its captured source.

    markdown-it's block parser strips each line's leading "> " before handing
    block rules their content, but dollarmath's display-math rule reads raw
    source lines instead, so a math_block token nested d blockquotes deep has
    up to d stray "> " prefixes on every line. Strip them back off so every
    consumer (HTML export, titles, captions) gets clean LaTeX.
    """
    depth = 0
    for token in state.tokens:
        if token.type == "blockquote_open":
            depth += 1
        elif token.type == "blockquote_close":
            depth -= 1
        elif token.type == "math_block" and depth > 0:
            lines = []
            for line in token.content.split("\n"):
                for _ in range(depth):
                    stripped = _BLOCKQUOTE_MARKER.sub("", line, count=1)
                    if stripped == line:
                        break
                    line = stripped
                lines.append(line)
            token.content = "\n".join(lines)


def new_parser() -> MarkdownIt:
    """A fresh parser. Take one whenever you need to add render rules."""
    md = (
        MarkdownIt("commonmark", {"html": False})
        .enable(["table", "strikethrough"])
        # $...$ and $$...$$ LaTeX. No spaces just inside the dollars and no digit
        # right after them, so prices like "$5 and $6" stay prose. Blank lines
        # are not allowed inside $$: without allow_blank_lines=False, an
        # unclosed "$$" pairs with the next "$$" anywhere later in the
        # document, swallowing every heading, figure link and paragraph in
        # between as literal math content.
        .use(
            dollarmath_plugin,
            allow_labels=False,
            allow_space=False,
            allow_digits=False,
            allow_blank_lines=False,
            double_inline=True,
        )
    )
    md.core.ruler.after("block", "lecnotes_math_in_blockquote", _strip_blockquote_markers)
    return md


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


def inline_text(children: list[Token]) -> str:
    """Plain text of inline tokens, keeping math as its LaTeX source.

    markdown-it's renderInlineAsText drops math tokens, which would turn
    "The $\\pi$ policy" into "The  policy" in titles and captions.
    """
    parts = []
    for token in children:
        if token.type in ("text", "code_inline", *_MATH_INLINE):
            parts.append(token.content)
        elif token.type == "image":
            parts.append(inline_text(token.children or []))
        elif token.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts)
