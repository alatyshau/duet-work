"""Source: Claude Exporter (claude.ai), markdown — one dialect of the
exporter family whose shared skeleton (sections, date lines, signature,
gaps from messages the page had not loaded) is in exporter_family.py.

'## User:' / '## Assistant:' sections in pairs, each with its own date on
the first line, as a quote ('> 2026/9/27 0:01:25'). The export often has a
JSON twin next to it, but that twin can't cleanly separate formatting from
the assistant's thinking/status quote — so the source used here is the
markdown, not the json.

The exporter saves only the messages the claude.ai page has loaded; a long
chat loads lazily from the bottom, so an export taken without scrolling to
the top can start with an '## Assistant:' section whose prompt is missing
(and the JSON twin holds that prompt as an empty string, not the text).
exporter_family marks such gaps instead of aborting.

Produced by the "AI Chat Exporter: Save Claude as PDF, MD and more" Chrome
extension — see the skill's
references/session_history_converter/chrome-exporters.md for the browser
extensions this tool's sources are known to correspond to.
"""

from pathlib import Path

from sources import exporter_family
from sources.exporter_family import QUOTED_DATE_LINE, Dialect, parse_quoted_date
from turns import Atom


def _split_response(body: list[str]) -> list[str]:
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
    return ["\n".join(body).strip("\n")]


DIALECT = Dialect(
    human_marker="## User:",
    ai_marker="## Assistant:",
    date_line=QUOTED_DATE_LINE,
    parse_date=parse_quoted_date,
    split_response=_split_response,
    footer=("Powered by Claude Exporter",),
)


def detect(path: Path) -> bool:
    # '## User:' alone is not enough since gemini_export shares it; convert.SOURCES
    # tries gemini_export first, so a file reaching here with only '## User:' is ours
    return exporter_family.has_line(path, DIALECT.human_marker, DIALECT.ai_marker)


def load_atoms(path: Path) -> list[Atom]:
    return exporter_family.load_atoms(path, DIALECT)
