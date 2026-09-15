"""The one Markdown parser configuration.

finish's figure validation and both exporters parse with this, so they can never
disagree about what counts as an image link.
"""

from collections.abc import Iterator

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.dollarmath import dollarmath_plugin

_MATH_INLINE = ("math_inline", "math_inline_double")


def new_parser() -> MarkdownIt:
    """A fresh parser. Take one whenever you need to add render rules."""
    return (
        MarkdownIt("commonmark", {"html": False})
        .enable(["table", "strikethrough"])
        # $...$ and $$...$$ LaTeX. No spaces just inside the dollars and no digit
        # right after them, so prices like "$5 and $6" stay prose.
        .use(
            dollarmath_plugin,
            allow_labels=False,
            allow_space=False,
            allow_digits=False,
            double_inline=True,
        )
    )


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
