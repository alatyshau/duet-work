#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Splits an AI conversation into one markdown file per human turn,
regardless of where it came from. This tool owns the output format; the
source is an implementation detail under sources/, and the list of sources
grows on its own, one file per source rather than one ever-growing script —
at 10-20 sources a monolith would stop being maintainable.

Sources today (sources/<module>.py, each exposing detect(path) and load_atoms(path)):

- **claude_jsonl** — a Claude Code session (`~/.claude/projects/*/<sessionId>.jsonl`).
  A turn can include tool calls, prompts that arrived while the agent was
  still working on the previous turn, and interrupts.
- **claude_export** — a claude.ai export, markdown, '## User:' / '## Assistant:' sections.
- **google_export** — a Google AI Mode export, markdown, '### AI Mode reply for ...'.
- **deepseek_export** — a DeepSeek share-page export, markdown with '### User' /
  'DeepSeek AI' markers whose assistant bodies are HTML; cleaned to markdown
  before rendering. Not yet regression-tested against a real export — see
  the module docstring.

See the skill's references/session_history_converter/known-sources.md for
sources that are documented but not yet implemented (no real example
exists in this project to test against).

To add a source: drop a `sources/<name>.py` with the same two functions and
register it with one line in SOURCES below. The output format (this file
and turns.py) doesn't need to change.

Output format — one markdown file per turn, `NN_MMDD_HHMM.md` (or `NN.md`
when the source carries no dates) next to the source file:

    ---
    turn: 1
    ---
    # Turn 01

    ## Opening Prompt
    [timestamp:: 2026-09-15 11:31:29]
    <the human's words, verbatim>

    ## Final Response
    [timestamp:: 2026-09-15 11:31:36]
    <the assistant's words, verbatim>

When a turn holds more than that pair (currently only the claude_jsonl
source produces this), `Tool_<Name>`, "Inline Prompt", "Intermediate
Response" and "Interrupt" sections appear between them, sharing one running
number within the file: `## Tool_Bash:01`, `## Intermediate Response:02`,
and so on. The model's reasoning (thinking) and tool call results are
never written to disk — this format captures what was said, not how the
model arrived at it.

Headings inside an AI response body (never a prompt) follow a separate
rule, see turns.apply_heading_rule: if the response opens with a heading,
and headings of that level occur exactly once in the whole response, that
heading is folded into the tail of the section heading (e.g. "## Final
Response: Migration plan"); otherwise every heading in the response is
shifted down so the shallowest one becomes H3.

Usage: uv run --script convert.py <path-to-source>
Writes the .md files next to the source file.
"""

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # must come before importing sibling modules,
sys.path.insert(0, str(Path(__file__).parent))  # or __pycache__ ends up on the synced drive

from turns import render_turn, split_turns, turn_filename  # noqa: E402
from sources import claude_export, claude_jsonl, deepseek_export, google_export  # noqa: E402

SOURCES = [claude_jsonl, google_export, deepseek_export, claude_export]  # cheapest/most specific detect() first, most general last

TURN_FILE_RE = re.compile(r"^\d{2,}(?:_\d{4}_\d{4})?\.md$")  # the names turn_filename() produces


def load_atoms(path: Path):
    for source in SOURCES:
        if source.detect(path):
            return source.load_atoms(path)
    sys.exit(f"unrecognized source: {path}")


def stale_turn_files(out_dir: Path, written: set[str]) -> list[str]:
    """Turn files in out_dir that this run did not write. Turns are numbered
    from 01, so if a re-run produces fewer turns than the last one did (the
    source changed, or a turn boundary moved), the leftover high-numbered
    files from before would silently sit next to the fresh ones and read as
    part of the same conversation. They are reported, never deleted."""
    return sorted(p.name for p in out_dir.iterdir() if TURN_FILE_RE.match(p.name) and p.name not in written)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: convert.py <path-to-source>")

    source_path = Path(sys.argv[1])
    atoms = load_atoms(source_path)
    turns = split_turns(atoms)

    out_dir = source_path.parent
    written: set[str] = set()
    for n, turn_atoms in enumerate(turns, start=1):
        name = turn_filename(n, turn_atoms)
        (out_dir / name).write_text(render_turn(n, turn_atoms), encoding="utf-8")
        written.add(name)

    print(f"{len(turns)} turns -> {out_dir}")
    stale = stale_turn_files(out_dir, written)
    if stale:
        print(
            f"warning: {len(stale)} turn file(s) from an earlier run were not rewritten and may be stale: "
            + ", ".join(stale),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
