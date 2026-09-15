"""Deck-name derivation.

The slug names the workdir and the output file, so it has to survive the
punctuation real lecture filenames carry (`lec8-txn,cc.pdf`) without erasing
names written in other scripts (`Übung 3.pdf`, `讲义.pdf`).
"""

import re

FALLBACK = "deck"


def slugify(name: str) -> str:
    # [\W_] is "not a Unicode letter or digit"; \w alone would keep underscores.
    return re.sub(r"[\W_]+", "-", name.casefold()).strip("-") or FALLBACK
