"""Source: Claude Exporter (claude.ai), markdown.

'## User:' / '## Assistant:' sections in pairs, each with its own date on
the first line. The export often has a JSON twin next to it, but that twin
can't cleanly separate formatting from the assistant's thinking/status
quote — so the source used here is the markdown, not the json.

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

DATE_LINE = re.compile(r"^> (\d{1,4})/(\d{1,4})/(\d{1,4}) (\d{2}):(\d{2}):(\d{2})\s*$")


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
    """Removes a leading quote block (the assistant's thinking/status) when
    present. Applied only to assistant sections: in a User section such a
    '>' quote can be part of the actual prompt, not a thought."""
    if not body or not body[0].startswith(">"):
        return body
    i = 0
    while i < len(body) and body[i].startswith(">"):
        i += 1
    while i < len(body) and body[i].strip() == "":
        i += 1
    return body[i:]


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
        sections.append((role, body))

    if len(sections) % 2 != 0:
        sys.exit(f"expected an even number of sections, got {len(sections)}")

    atoms: list[Atom] = []
    for i in range(0, len(sections), 2):
        (h_role, h_raw), (a_role, a_raw) = sections[i], sections[i + 1]
        if h_role != "human" or a_role != "assistant":
            sys.exit(f"sections {i}/{i + 1} are not a User/Assistant pair ({h_role}/{a_role})")
        h_time, h_body = _extract_timestamp(h_raw)
        a_time, a_body = _extract_timestamp(a_raw)
        a_body = _strip_thoughts(a_body)  # heading normalization happens in turns.render_section
        atoms.append(Atom("prompt", text="\n".join(h_body).strip("\n"), timestamp=h_time))
        atoms.append(Atom("response", text="\n".join(a_body).strip("\n"), timestamp=a_time))
    return atoms
