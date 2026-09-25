"""Shared output model — independent of where the conversation came from.

A source module (see sources/) reduces its input to a list of Atoms in
event order. Everything downstream — grouping atoms into turns and
rendering them to markdown — is handled once, here, the same way for every
source. Adding a source never requires touching this file.

The output format itself is documented in convert.py's module docstring.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime

HEADING = re.compile(r"^(#{1,6})(\s+.*)$")

# Section labels. Kept as named constants, not inlined, so the vocabulary
# is easy to audit or change in one place without touching the rendering
# logic itself.
TURN_LABEL = "Turn"
HEADING_START_PROMPT = "Opening Prompt"
HEADING_INLINE_PROMPT = "Inline Prompt"
HEADING_INTERMEDIATE_RESPONSE = "Intermediate Response"
HEADING_FINAL_RESPONSE = "Final Response"
HEADING_INTERRUPT = "Interrupt"
HEADING_TOOL_CALL_PREFIX = "Tool_"


@dataclass
class Atom:
    kind: str  # 'prompt' | 'response' | 'tool_call' | 'interrupt'
    text: str = ""
    tool_name: str = ""
    tool_input: dict = field(default_factory=dict)
    timestamp: datetime | None = None


def split_turns(atoms: list[Atom]) -> list[list[Atom]]:
    """A prompt right after a response starts a new turn. A prompt right
    after a tool call, an interrupt, or another prompt stays in the same
    turn — it either extends the opening prompt or becomes an inline
    prompt, which render_turn decides from its position in the turn."""
    turns: list[list[Atom]] = []
    current: list[Atom] = []
    last_kind: str | None = None
    for atom in atoms:
        if atom.kind == "prompt" and last_kind == "response":
            if current:
                turns.append(current)
            current = [atom]
        else:
            current.append(atom)
        last_kind = atom.kind
    if current:
        turns.append(current)
    return turns


FENCE = re.compile(r"^\s*(```|~~~)")


def headings_outside_fences(lines: list[str]) -> list[tuple[int, re.Match]]:
    """Every markdown heading in `lines` that is not inside a fenced code
    block, as (line index, regex match). A `# comment` in a shell or Python
    snippet looks exactly like a heading to a line regex; treating it as one
    would both miscount the document's real headings and rewrite the code
    itself when levels get shifted."""
    found = []
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence and (m := HEADING.match(line)):
            found.append((i, m))
    return found


def normalize_headings(body: list[str]) -> list[str]:
    """Shifts headings down so the shallowest one becomes H3. Lines inside
    fenced code blocks are never touched."""
    headings = headings_outside_fences(body)
    if not headings:
        return body
    shift = max(0, 3 - min(len(m.group(1)) for _, m in headings))
    if shift == 0:
        return body
    out = list(body)
    for i, m in headings:
        out[i] = "#" * (len(m.group(1)) + shift) + m.group(2)
    return out


def apply_heading_rule(text: str) -> tuple[str, str]:
    """Heading rule for an AI response body.

    If the text opens with a heading, and headings of that same level occur
    exactly once in the whole text, that heading is folded into the tail of
    our own section heading (e.g. "## Final Response: Migration plan") and
    removed from the body. Otherwise every heading in the text is shifted
    down so the shallowest one becomes H3 — this also covers the case where
    the leading heading isn't unique, or isn't first.

    The special case exists because many assistants open a reply with their
    own single top-level heading (a title, a numbered response header from
    another convention, etc.); folding it into our section heading avoids a
    redundant, confusingly-nested duplicate heading right under it.

    Returns (suffix for the section heading, processed body).
    """
    lines = text.split("\n")
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    headings = headings_outside_fences(lines)
    # the response "opens with a heading" only if the first non-blank line is
    # a real heading — a code fence opener on that line is not one
    first_heading = next((m for idx, m in headings if idx == i), None)

    if first_heading is not None:
        lead_level = len(first_heading.group(1))
        same_level_count = sum(1 for _, m in headings if len(m.group(1)) == lead_level)
        if same_level_count == 1:
            title = first_heading.group(2).strip()
            rest = lines[i + 1 :]
            while rest and rest[0].strip() == "":
                rest.pop(0)
            return f": {title}", "\n".join(normalize_headings(rest)).strip("\n")

    return "", "\n".join(normalize_headings(lines)).strip("\n")


def render_section(heading: str, atom: Atom) -> str:
    suffix, text = ("", atom.text.strip("\n"))
    if atom.kind == "response":
        suffix, text = apply_heading_rule(atom.text)
    parts = [heading + suffix]
    if atom.timestamp is not None:
        parts.append(f"[timestamp:: {atom.timestamp:%Y-%m-%d %H:%M:%S}]")
    parts.append("")
    parts.append(text)
    return "\n".join(parts)


def render_tool_call(heading: str, atom: Atom) -> str:
    lines = [heading, ""]
    for key, value in atom.tool_input.items():
        rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        lines.append(f"**{key}:** {rendered}")
    return "\n".join(lines)


def render_turn(n: int, atoms: list[Atom]) -> str:
    # leading run of prompt atoms, before any response or tool call, is the opening prompt
    lead_end = 0
    while lead_end < len(atoms) and atoms[lead_end].kind == "prompt":
        lead_end += 1
    lead = atoms[:lead_end]
    rest = atoms[lead_end:]

    start_text = "\n\n".join(a.text for a in lead if a.text)
    start_atom = Atom("prompt", text=start_text, timestamp=lead[0].timestamp if lead else None)
    sections = [render_section(f"## {HEADING_START_PROMPT}", start_atom)]

    last_response_idx = max((i for i, a in enumerate(rest) if a.kind == "response"), default=None)

    counter = 0
    final_section = None
    for i, atom in enumerate(rest):
        if atom.kind == "response" and i == last_response_idx:
            final_section = render_section(f"## {HEADING_FINAL_RESPONSE}", atom)
            continue
        counter += 1
        if atom.kind == "prompt":
            sections.append(render_section(f"## {HEADING_INLINE_PROMPT}:{counter:02d}", atom))
        elif atom.kind == "response":
            sections.append(render_section(f"## {HEADING_INTERMEDIATE_RESPONSE}:{counter:02d}", atom))
        elif atom.kind == "tool_call":
            sections.append(render_tool_call(f"## {HEADING_TOOL_CALL_PREFIX}{atom.tool_name}:{counter:02d}", atom))
        elif atom.kind == "interrupt":
            heading = f"## {HEADING_INTERRUPT}:{counter:02d}"
            if atom.timestamp is not None:
                heading += f"\n[timestamp:: {atom.timestamp:%Y-%m-%d %H:%M:%S}]"
            sections.append(heading)

    if final_section:
        sections.append(final_section)

    body = "\n\n".join(sections)
    return f"---\nturn: {n}\n---\n# {TURN_LABEL} {n:02d}\n\n{body}\n"


def turn_filename(n: int, atoms: list[Atom]) -> str:
    first_ts = next((a.timestamp for a in atoms if a.timestamp), None)
    suffix = f"_{first_ts:%m%d_%H%M}" if first_ts else ""
    return f"{n:02d}{suffix}.md"
