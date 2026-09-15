#!/usr/bin/env bash
# usage: ledger-commit.sh "<progress line>" ["<deferred minor line>"]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
W=docs/superpowers/sdd/2026-08-27-lecnotes
python3 - "$W/progress.md" "$1" "${2:-}" <<'PY'
import sys
p, prog, minor = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p).read()
if minor:
    s = s.replace("\n## Progress\n", f"- {minor}\n\n## Progress\n", 1)
s = s.rstrip("\n") + f"\n- {prog}\n"
open(p, "w").write(s)
PY
git add "$W"
git commit -q -m "SDD: ${1%% (*}

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy"
git push -q
git rev-parse --short HEAD
