"""Deck-name derivation.

The slug names the workdir and the output file, so it has to survive the
punctuation real lecture filenames carry (`lec8-txn,cc.pdf`).
"""

import re


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
