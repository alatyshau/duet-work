"""Source: Claude Exporter (claude.ai), markdown.

'## User:' / '## Assistant:' sections in pairs, each with its own date on
the first line. The export often has a JSON twin next to it, but that twin
can't cleanly separate formatting from the assistant's thinking/status
quote — so the source used here is the markdown, not the json.

The exporter saves only the messages the claude.ai page has loaded; a long
chat loads lazily from the bottom, so an export taken without scrolling to
the top can start with an '## Assistant:' section whose prompt is missing
(and the JSON twin holds that prompt as an empty string, not the text).
Such a gap — an assistant section with no user section before it, or two
user sections in a row — doesn't abort the run: the missing side becomes a
visible marker (MISSING_PROMPT / MISSING_RESPONSE) so the turn boundary
stays where it was, and a warning names each gap, since scrolling the chat
up and exporting again recovers the real text.

Produced by the "AI Chat Exporter: Save Claude as PDF, MD and more" Chrome
extension — see the skill's
references/session_history_converter/chrome-exporters.md for the browser
extensions this tool's sources are known to correspond to.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

from turns import Atom

# the exporter doesn't zero-pad the hour ("2026/9/27 0:01:25"), hence \d{1,2}
DATE_LINE = re.compile(r"^> (\d{1,4})/(\d{1,4})/(\d{1,4}) (\d{1,2}):(\d{1,2}):(\d{1,2})\s*$")
FOOTER_PREFIX = "Powered by Claude Exporter"
MISSING_PROMPT = "*[prompt missing from the export — the page had not loaded it; scroll the chat up and export again to recover it]*"
MISSING_RESPONSE = "*[response missing from the export — the page had not loaded it; scroll the chat up and export again to recover it]*"


def detect(path: Path) -> bool:
    if path.suffix != ".md":
        return False
    lines = path.read_text(encoding="utf-8").split("\n")
    return any(line in ("## User:", "## Assistant:") for line in lines)


def _parse_date(m: re.Match) -> datetime:
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


def _strip_thoughts(body: list[str]) -> list[str]:
    """Removes the leading quote blocks (the assistant's thinking/status)
    when present. The exporter renders each thinking/status widget as its
    own quote block, and a long agentic answer can carry several of them
    before its visible text, separated by blank lines — so blocks are
    stripped one after another until the body no longer starts with a
    quote. Applied only to assistant sections: in a User section such a
    '>' quote can be part of the actual prompt, not a thought."""
    while body and body[0].startswith(">"):
        i = 0
        while i < len(body) and body[i].startswith(">"):
            i += 1
        while i < len(body) and body[i].strip() == "":
            i += 1
        body = body[i:]
    return body


def _strip_footer(body: list[str]) -> list[str]:
    """Drops the exporter's signature — the last non-blank line of the file,
    which lands inside the last section's body."""
    i = len(body)
    while i > 0 and body[i - 1].strip() == "":
        i -= 1
    if i > 0 and body[i - 1].startswith(FOOTER_PREFIX):
        return body[: i - 1]
    return body


def _extract_timestamp(body: list[str]) -> tuple[datetime, list[str]]:
    i = 0
    while i < len(body) and body[i].strip() == "":
        i += 1
    m = DATE_LINE.match(body[i])
    if not m:
        raise ValueError(f"expected a date line, found: {body[i]!r}")
    time = _parse_date(m)
    i += 1
    while i < len(body) and body[i].strip() == "":
        i += 1
    return time, body[i:]


def load_atoms(path: Path) -> list[Atom]:
    lines = path.read_text(encoding="utf-8").split("\n")

    sections: list[tuple[str, list[str]]] = []
    role: str | None = None
    body: list[str] = []
    for line in lines:
        if line in ("## User:", "## Assistant:"):
            if role is not None:
                sections.append((role, body))
            role = "human" if line == "## User:" else "assistant"
            body = []
        elif role is not None:
            body.append(line)
    if role is not None:
        sections.append((role, _strip_footer(body)))

    # claude.ai strictly alternates User/Assistant, so a repeated role (or an
    # Assistant first) means the exporter skipped a message, not that the chat
    # really had one; the marker keeps the turn split where it belongs
    atoms: list[Atom] = []
    gaps: list[str] = []
    prev_role: str | None = None
    for role, raw in sections:
        time, body = _extract_timestamp(raw)
        if role == "human":
            if prev_role == "human":
                atoms.append(Atom("response", text=MISSING_RESPONSE))
                gaps.append(f"response before the prompt of {time:%Y-%m-%d %H:%M:%S}")
            atoms.append(Atom("prompt", text="\n".join(body).strip("\n"), timestamp=time))
        else:
            if prev_role != "human":
                atoms.append(Atom("prompt", text=MISSING_PROMPT))
                gaps.append(f"prompt before the response of {time:%Y-%m-%d %H:%M:%S}")
            body = _strip_thoughts(body)  # heading normalization happens in turns.render_section
            atoms.append(Atom("response", text="\n".join(body).strip("\n"), timestamp=time))
        prev_role = role

    for gap in gaps:
        print(f"warning: {path.name}: missing {gap} (not loaded on the page when exported)", file=sys.stderr)
    return atoms
