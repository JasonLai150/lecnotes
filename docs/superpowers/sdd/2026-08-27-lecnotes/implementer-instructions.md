# Implementer instructions

You are implementing one task of `lecnotes`, a Python CLI that turns one lecture deck (.pdf/.pptx) into a self-contained workdir a coding agent reads to write a teaching document, plus a command that validates and assembles the result.

Work from: /Users/jasonlai150/Documents/GitHub/lecnotes

All paths below are in /Users/jasonlai150/Documents/GitHub/lecnotes/docs/superpowers/sdd/2026-08-27-lecnotes/ . Your dispatch message tells you the task number N.

## Read first
1. `task-N-brief.md` — your requirements, with the exact values to use verbatim. It is the single source of requirements.
2. `global-constraints.md` — project-wide constraints and the file-structure map that bind every task.
Do not read the whole plan file.

## Environment
- `uv` is at ~/.local/bin/uv and the environment is synced. Run tests with `uv run pytest`.
- Commit on `main`. Do NOT push. Do not commit anything under docs/.
- Every commit message must end with exactly these two lines:
  Co-Authored-By: Claude <your model name> <noreply@anthropic.com>   (name the model you are running as)
  Claude-Session: https://claude.ai/code/session_01YAyFL8DWShjsveMRqBQ4Dy

## Process
TDD exactly as the brief lays out: write the failing test, run it and see it fail for the expected reason, implement, see it pass. While iterating run the focused test; run the full suite once before committing.

If the brief's code does not behave as the brief says (for example a pymupdf API behaves differently than the brief assumes), you may make the smallest change that satisfies the brief's stated intent — and you must describe every such deviation in your report and return DONE_WITH_CONCERNS. If the right fix is a genuine design choice, stop and return NEEDS_CONTEXT or BLOCKED with specifics. Never weaken a test's assertion just to make it pass without reporting it.

Follow the plan's file structure. Don't restructure beyond your task.

## You do not dispatch subagents
Do all the work yourself. Never spawn a subagent, and above all never spawn a reviewer — review is scheduled by the controller after you report.

## Self-review before reporting
Read your own diff with fresh eyes. Completeness (everything in the brief, edge cases), quality (clear names, clean code), discipline (nothing extra, YAGNI), testing (real behavior, TDD followed, output pristine). Fix what you find before reporting.

## After review findings
If resumed with findings: fix them, re-run the tests covering the amended code, and APPEND a fix report to your report file (what changed, covering tests, command, output). Then reply with the same short contract.

## Report
Write your full report to `task-N-report.md`: what you implemented; TDD evidence (RED: command, relevant failing output, why expected; GREEN: command, passing output); files changed; deviations from the brief; self-review findings; concerns.

Then reply with ONLY (under 15 lines):
- Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits created (short SHA + subject)
- One-line test summary
- Concerns, if any
- The report file path
If BLOCKED or NEEDS_CONTEXT, put the specifics in the reply itself.
