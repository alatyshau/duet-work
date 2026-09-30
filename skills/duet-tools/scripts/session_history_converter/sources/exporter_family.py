"""The shared skeleton of the markdown exports made by one family of Chrome
extensions — Claude Exporter (claude.ai), ChatGPT Exporter (chatgpt.com)
and the Gemini exporter (gemini.google.com). Not a source itself: each of
claude_export, chatgpt_export and gemini_export describes its dialect
with a Dialect and hands it to load_atoms here.

What the family shares, and so lives only here:

- a title and a '**...:**' header, then sections opened by a line that is
  exactly the human marker or the AI marker ('## User:' / '## Assistant:',
  '## Prompt:' / '## Response:', '## User:' / '## Gemini:');
- a date line as the first non-blank line of every section;
- an optional signature at the end of the file, which lands inside the last
  section and is dropped;
- strict alternation in the chat itself, so a repeated role, or an AI
  section first, means the exporter skipped a message the page had not
  loaded — the missing side becomes a visible marker (MISSING_PROMPT /
  MISSING_RESPONSE), which keeps the turn boundary where it belongs, and a
  warning names each gap, since scrolling the chat up and exporting again
  recovers the real text.

What differs per dialect: the markers, the date line and how to read it,
the signature, and how the model's reasoning is cut out of an AI section —
each provider renders it differently, so that rule is the dialect's own
split_response, which returns the section's texts in order: every text but
the last becomes an Intermediate Response, the last the Final Response.
"""

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from turns import Atom

MISSING_PROMPT = "*[prompt missing from the export — the page had not loaded it; scroll the chat up and export again to recover it]*"
MISSING_RESPONSE = "*[response missing from the export — the page had not loaded it; scroll the chat up and export again to recover it]*"

# the date line of Claude Exporter and the Gemini exporter, as a quote:
# '> 2026/9/27 0:01:25' or '> 9/15/2026 11:31:29' — the hour isn't zero-padded
QUOTED_DATE_LINE = re.compile(r"^> (\d{1,4})/(\d{1,4})/(\d{1,4}) (\d{1,2}):(\d{1,2}):(\d{1,2})\s*$")


def parse_quoted_date(m: re.Match) -> datetime:
    """M/D/Y or Y/M/D — the exporter emits one order or the other; told
    apart by which group has four digits (the year)."""
    a, b, c, hh, mm, ss = m.groups()
    if len(a) == 4:
        year, month, day = a, b, c
    elif len(c) == 4:
        month, day, year = a, b, c
    else:
        raise ValueError(f"could not parse date: {m.group(0)!r}")
    return datetime(int(year), int(month), int(day), int(hh), int(mm), int(ss))


@dataclass(frozen=True)
class Dialect:
    human_marker: str
    ai_marker: str
    date_line: re.Pattern
    parse_date: Callable[[re.Match], datetime]
    split_response: Callable[[list[str]], list[str]]
    # the signature's lines from the bottom up, each matched as a prefix; the
    # first must match for anything to be dropped, the rest are dropped while
    # they match (ChatGPT Exporter puts a '---' rule above its line)
    footer: tuple[str, ...] = ()


def has_line(path: Path, *wanted: str, mentions: str | None = None) -> bool:
    """For detect(): an .md file with a line that is exactly one of `wanted`
    and, when `mentions` is given, that text somewhere in it — the
    provider's domain, which the header's link carries, so that a marker
    line alone (quoted inside another provider's chat, say) isn't enough."""
    if path.suffix != ".md":
        return False
    text = path.read_text(encoding="utf-8")
    if mentions is not None and mentions not in text:
        return False
    return any(line in wanted for line in text.split("\n"))


def strip_blocks(body: list[str], is_reasoning: Callable[[list[str]], bool]) -> list[list[str]]:
    """Cuts the quote blocks `is_reasoning` recognizes out of an AI section
    and returns the pieces between them. A quote block is a run of lines
    starting with '>'; one that isn't reasoning (a quote of the person, say)
    stays in its piece."""
    pieces: list[list[str]] = [[]]
    i = 0
    while i < len(body):
        if not body[i].startswith(">"):
            pieces[-1].append(body[i])
            i += 1
            continue
        start = i
        while i < len(body) and body[i].startswith(">"):
            i += 1
        block = body[start:i]
        if is_reasoning(block):
            pieces.append([])
        else:
            pieces[-1].extend(block)
    return pieces


def _strip_footer(body: list[str], footer: tuple[str, ...]) -> list[str]:
    def last_non_blank(end: int) -> int:
        while end > 0 and body[end - 1].strip() == "":
            end -= 1
        return end

    i = last_non_blank(len(body))
    if not footer or i == 0 or not body[i - 1].startswith(footer[0]):
        return body
    i -= 1
    for prefix in footer[1:]:
        j = last_non_blank(i)
        if j == 0 or not body[j - 1].startswith(prefix):
            break
        i = j - 1
    return body[:i]


def _extract_timestamp(body: list[str], dialect: Dialect) -> tuple[datetime, list[str]]:
    i = 0
    while i < len(body) and body[i].strip() == "":
        i += 1
    m = dialect.date_line.match(body[i]) if i < len(body) else None
    if not m:
        raise ValueError(f"expected a date line, found: {body[i] if i < len(body) else None!r}")
    time = dialect.parse_date(m)
    i += 1
    while i < len(body) and body[i].strip() == "":
        i += 1
    return time, body[i:]


def load_atoms(path: Path, dialect: Dialect) -> list[Atom]:
    lines = path.read_text(encoding="utf-8").split("\n")

    sections: list[tuple[str, list[str]]] = []
    role: str | None = None
    body: list[str] = []
    for line in lines:
        if line in (dialect.human_marker, dialect.ai_marker):
            if role is not None:
                sections.append((role, body))
            role = "human" if line == dialect.human_marker else "ai"
            body = []
        elif role is not None:
            body.append(line)
    if role is not None:
        sections.append((role, _strip_footer(body, dialect.footer)))

    atoms: list[Atom] = []
    gaps: list[str] = []
    prev_role: str | None = None
    for role, raw in sections:
        time, body = _extract_timestamp(raw, dialect)
        if role == "human":
            if prev_role == "human":
                atoms.append(Atom("response", text=MISSING_RESPONSE))
                gaps.append(f"response before the prompt of {time:%Y-%m-%d %H:%M:%S}")
            atoms.append(Atom("prompt", text="\n".join(body).strip("\n"), timestamp=time))
        else:
            if prev_role != "human":
                atoms.append(Atom("prompt", text=MISSING_PROMPT))
                gaps.append(f"prompt before the response of {time:%Y-%m-%d %H:%M:%S}")
            # heading normalization happens in turns.render_section
            for text in dialect.split_response(body):
                atoms.append(Atom("response", text=text, timestamp=time))
        prev_role = role

    for gap in gaps:
        print(f"warning: {path.name}: missing {gap} (not loaded on the page when exported)", file=sys.stderr)
    return atoms
