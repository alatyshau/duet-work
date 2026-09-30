"""Source: a Gemini (gemini.google.com) chat exported to markdown — one
dialect of the exporter family whose shared skeleton (sections, date lines,
gaps from messages the page had not loaded) is in exporter_family.py.

'## User:' / '## Gemini:' sections in pairs, each with its own date on the
first line, as a quote ('> 2026/9/27 22:11:36'), the same date line Claude
Exporter writes. The file opens with a title and an '**Exported:** /
**Link:** https://gemini.google.com/app/...' header and carries no
signature at the end.

A Gemini section usually opens with the model's reasoning as one quote
block, '> **Thinking steps**' followed by its steps; that block is dropped.
Only that block is: a reply that happens to open with a real quote keeps
it. Everything else — the '[cite: N]' marks Gemini leaves where it drew on
an attached file, the '- name (type)' lines listing a prompt's attachments —
stays verbatim.

Checked against one real export (36 turns, 2026-09-29). Which Chrome
extension produced it isn't recorded — see the skill's
references/session_history_converter/chrome-exporters.md.
"""

from pathlib import Path

from sources import exporter_family
from sources.exporter_family import QUOTED_DATE_LINE, Dialect, parse_quoted_date
from turns import Atom

THINKING_HEAD = "> **Thinking steps**"


def _split_response(body: list[str]) -> list[str]:
    """Drops the leading 'Thinking steps' quote block, if there is one."""
    if body and body[0] == THINKING_HEAD:
        i = 0
        while i < len(body) and body[i].startswith(">"):
            i += 1
        body = body[i:]
    return ["\n".join(body).strip("\n")]


DIALECT = Dialect(
    human_marker="## User:",
    ai_marker="## Gemini:",
    date_line=QUOTED_DATE_LINE,
    parse_date=parse_quoted_date,
    split_response=_split_response,
)


def detect(path: Path) -> bool:
    return exporter_family.has_line(path, DIALECT.ai_marker, mentions="gemini.google.com")


def load_atoms(path: Path) -> list[Atom]:
    return exporter_family.load_atoms(path, DIALECT)
