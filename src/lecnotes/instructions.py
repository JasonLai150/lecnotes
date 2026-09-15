"""Fill the agent-facing contract template.

Placeholders are {{name}}. The template teaches LaTeX, so it is full of dollar
signs; string.Template's $-placeholders would collide with them.
"""

import re
from importlib.resources import files

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def render_instructions(deck: str, slides: int, source_name: str) -> str:
    raw = files("lecnotes.templates").joinpath("instructions.md").read_text(encoding="utf-8")
    values = {"deck": deck, "slides": str(slides), "source_name": source_name}
    # One pass, so a value that itself contains "{{...}}" is never re-expanded.
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], raw)
