"""Source: ChatGPT Exporter (chatgpt.com), markdown — one dialect of the
exporter family whose shared skeleton (sections, date lines, signature,
gaps from messages the page had not loaded) is in exporter_family.py.

'## Prompt:' / '## Response:' sections in pairs. The first line of each
body is its date in US order with a 12-hour clock, and on a response the
model after a middle dot:

    9/27/2026, 9:54:58 PM
    9/28/2026, 12:33:32 AM · gpt-6-pro

The file opens with a title and a '**Created:** / **Updated:** /
**Exported:** / **Link:** https://chatgpt.com/c/...' header and ends with
the exporter's signature, '---' and 'Powered by [ChatGPT Exporter](...)'.

A response can hold, before its answer, what the model showed while it
worked: one or more short progress messages as plain paragraphs (often in
English, sometimes a real first reply in the chat's language), and its
reasoning as a quote block — '> **Heading**' steps ending in the line
'> Worked for 33s'. A reasoning block is recognized by that last line
('Worked for' or 'Thought for'), never by its first, because a response or a
prompt can also quote the person with '> **...**'. Reasoning blocks are
dropped; the text after the last of them is the Final Response, and text
before or between them becomes Intermediate Responses, since the person saw
it and it sometimes carries the substance. Prompts are never touched.

Produced by the "ChatGPT Exporter - ChatGPT to PDF, MD, and more" Chrome
extension (signature above) — see the skill's
references/session_history_converter/chrome-exporters.md. Checked against
one real export (132 turns, 2026-09-29).
"""

import re
from datetime import datetime
from pathlib import Path

from sources import exporter_family
from sources.exporter_family import Dialect
from turns import Atom

DATE_LINE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4}), (\d{1,2}):(\d{2}):(\d{2}) (AM|PM)(?: · (.+))?\s*$")
REASONING_END = re.compile(r"^> (Worked|Thought) for \S")


def _parse_date(m: re.Match) -> datetime:
    """Parsed by hand rather than with strptime's %p, which follows the
    machine's locale and would not match 'PM' under a Russian one."""
    month, day, year, hh, mm, ss, ampm = m.groups()[:7]
    hour = int(hh) % 12 + (12 if ampm == "PM" else 0)
    return datetime(int(year), int(month), int(day), hour, int(mm), int(ss))


def _split_response(body: list[str]) -> list[str]:
    pieces = exporter_family.strip_blocks(body, lambda block: bool(REASONING_END.match(block[-1])))
    texts = ["\n".join(piece).strip("\n") for piece in pieces]
    return [t for t in texts if t.strip()] or [""]


DIALECT = Dialect(
    human_marker="## Prompt:",
    ai_marker="## Response:",
    date_line=DATE_LINE,
    parse_date=_parse_date,
    split_response=_split_response,
    footer=("Powered by [ChatGPT Exporter]", "---"),
)


def detect(path: Path) -> bool:
    return exporter_family.has_line(path, DIALECT.ai_marker, mentions="chatgpt.com")


def load_atoms(path: Path) -> list[Atom]:
    return exporter_family.load_atoms(path, DIALECT)
