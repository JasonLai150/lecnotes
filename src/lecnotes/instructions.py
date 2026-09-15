"""Fill the agent-facing contract template.

string.Template is deliberate: the template is full of Markdown braces and
backticks, and $-substitution leaves all of them alone.
"""

from importlib.resources import files
from string import Template


def render_instructions(
    deck: str, slides: int, figures: int, source_name: str, workdir_name: str
) -> str:
    raw = files("lecnotes.templates").joinpath("instructions.md").read_text(encoding="utf-8")
    return Template(raw).substitute(
        deck=deck,
        slides=slides,
        figures=figures,
        source_name=source_name,
        workdir_name=workdir_name,
    )
