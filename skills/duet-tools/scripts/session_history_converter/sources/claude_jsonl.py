"""Source: a Claude Code session (.jsonl under ~/.claude/projects/*/).

A turn can include tool calls, prompts that arrived while the agent was
still working on the previous turn and got folded into it, and interrupts.
The model's reasoning (thinking blocks) and tool call results are not kept —
this converter renders what was said, not how it was produced.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from turns import Atom

INTERRUPT_TEXT = "[Request interrupted by user]"
SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>\s*", re.DOTALL)
LOCAL_COMMAND_RE = re.compile(r"<local-command-(caveat|stdout)>.*?</local-command-\1>\s*", re.DOTALL)
COMMAND_MESSAGE_RE = re.compile(r"<command-message>.*?</command-message>\s*", re.DOTALL)
COMMAND_RE = re.compile(r"<command-name>(.*?)</command-name>(?:\s*<command-args>(.*?)</command-args>)?", re.DOTALL)


def detect(path: Path) -> bool:
    return path.suffix == ".jsonl"


def clean_prompt_text(text: str) -> str:
    """What the human actually typed, with the client's own wrappers removed.

    Claude Code wraps a human turn in markup of its own: <system-reminder>
    blocks of injected context, <local-command-caveat>/<local-command-stdout>
    blocks holding the output of a local slash command the person ran, and
    <command-message>/<command-name>/<command-args> around a slash command.
    None of that markup is the person's words. The one thing worth keeping
    from it is the command itself, so `<command-name>/x</command-name>
    <command-args>y</command-args>` is rendered as `/x y` — exactly what was
    typed — and the rest is dropped.
    """
    text = SYSTEM_REMINDER_RE.sub("", text)
    text = LOCAL_COMMAND_RE.sub("", text)
    text = COMMAND_MESSAGE_RE.sub("", text)
    text = COMMAND_RE.sub(
        lambda m: m.group(1).strip() + (" " + m.group(2).strip() if m.group(2) and m.group(2).strip() else ""),
        text,
    )
    return text.strip()


def parse_timestamp(raw: str | None) -> datetime | None:
    """The record stores UTC; the output shows the converting machine's local
    time, deliberately. A Claude Code session lives on one machine and is
    converted there, so local time is the time the person actually lived in
    — and if they were travelling, the shift in timezone is meant to show.
    Not a bug to normalize away to UTC."""
    if not raw:
        return None
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return dt.astimezone()


def _record_atoms(record: dict) -> list[Atom]:
    """One JSONL record -> zero or more atoms.

    A "user"-role record isn't always something the human typed: Claude Code
    also injects skill files, environment notes and similar context as
    user-role messages. `origin.kind == "human"` is how a record marks
    itself as the person's own words; anything else with plain text content
    is dropped, the same way tool_result/thinking/image already are — it's
    context the harness added, not something said in the conversation. The
    interrupt marker is the one exception: it always has `origin: null`
    (it's synthetic too) but still represents a real human action, so it's
    checked before the origin filter, not after.
    """
    msg = record.get("message")
    if not isinstance(msg, dict):
        return []
    role = msg.get("role")
    content = msg.get("content")
    ts = parse_timestamp(record.get("timestamp"))
    origin = record.get("origin")
    is_human = isinstance(origin, dict) and origin.get("kind") == "human"
    atoms: list[Atom] = []

    if isinstance(content, str):
        if role == "user":
            if content.strip() == INTERRUPT_TEXT:
                atoms.append(Atom("interrupt", timestamp=ts))
            elif is_human:
                atoms.append(Atom("prompt", text=clean_prompt_text(content), timestamp=ts))
        return atoms

    if not isinstance(content, list):
        return atoms

    for block in content:
        if not isinstance(block, dict):
            continue
        bt = block.get("type")
        if bt == "text":
            text = block.get("text", "")
            if role == "user":
                if text.strip() == INTERRUPT_TEXT:
                    atoms.append(Atom("interrupt", timestamp=ts))
                elif is_human:
                    atoms.append(Atom("prompt", text=clean_prompt_text(text), timestamp=ts))
            elif role == "assistant":
                atoms.append(Atom("response", text=text, timestamp=ts))
        elif bt == "tool_use":
            atoms.append(
                Atom("tool_call", tool_name=block.get("name", "?"), tool_input=block.get("input", {}) or {}, timestamp=ts)
            )
        elif bt in ("tool_result", "thinking", "image"):
            continue
        else:
            print(f"warning: unknown content block type {bt!r}, skipped", file=sys.stderr)
    return atoms


def load_atoms(path: Path) -> list[Atom]:
    atoms: list[Atom] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("type") in ("user", "assistant"):
                atoms.extend(_record_atoms(record))
    return atoms
