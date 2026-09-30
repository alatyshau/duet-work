"""Local Codex / ChatGPT Code / Work rollout logs, not browser exports.

response_item is the canonical stream; event_msg often repeats it. Human
UI events, when present, distinguish real prompts from injected user context.
Compaction replacement_history is model context, never conversation history.
"""
import json
import re
import sys
from pathlib import Path

from turns import Atom
from sources.claude_jsonl import parse_timestamp


def records(path: Path):
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: invalid JSON; stop the session and retry a complete snapshot") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number}: expected a JSON object")
            yield value


def detect(path: Path) -> bool:
    if path.suffix.lower() != ".jsonl":
        return False
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    return False
                return isinstance(record, dict) and record.get("type") == "session_meta"
    return False


def content_text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        kind = block.get("type", "").lower()
        if kind in ("input_text", "output_text", "text"):
            parts.append(block.get("text", ""))
        elif kind in ("input_image", "image", "localimage", "local_image"):
            # Keep an honest marker, not megabytes of embedded base64.
            path = block.get("path") or block.get("image_url") or block.get("url")
            if not isinstance(path, str) or path.startswith("data:"):
                path = "embedded image; see original session"
            parts.append(f"[Image: {path}]")
        else:
            print(f"warning: unsupported Codex content block {kind!r}; retained only in source", file=sys.stderr)
            parts.append(f"[Unsupported content: {kind} — see original session]")
    return "\n".join(parts)


# Only remove leading harness envelopes in legacy logs without human events.
# Never delete matching tags inside quoted prose or code supplied by the user.
ENVELOPE = re.compile(r"^\s*<(environment_context|recommended_plugins|permissions instructions|skills_instructions)>.*?</\1>\s*", re.S)


def legacy_prompt(text: str) -> str:
    while match := ENVELOPE.match(text):
        text = text[match.end():]
    if text.startswith("# AGENTS.md instructions for ") or text.startswith("<INSTRUCTIONS>"):
        return ""
    return text.strip()


def human_event(payload: dict) -> str | None:
    if payload.get("type") == "user_message":
        text = payload.get("message", "")
        # Legacy event images can differ from the response stream representation.
        return text
    if payload.get("type") == "item_completed":
        item = payload.get("item", {})
        if item.get("type", "").lower() == "usermessage":
            return content_text(item.get("content", []))
    return None


def load_atoms(path: Path) -> list[Atom]:
    rows = list(records(path))
    if any(r.get("type") == "event_msg" and r.get("payload", {}).get("type") == "thread_rolled_back" for r in rows):
        raise ValueError("session contains thread_rolled_back; branch reconstruction is not supported")
    # Scope event validation by actual turn, not globally by text: a quoted
    # prompt or a genuinely repeated request must not be mistaken for a replay.
    humans: dict[str | None, list[str]] = {}
    active = None
    for row in rows:
        p = row.get("payload", {})
        if row.get("type") == "event_msg":
            if p.get("type") == "task_started":
                active = p.get("turn_id")
            text = human_event(p)
            if text is not None:
                humans.setdefault(p.get("turn_id") or active, []).append(text)
        elif row.get("type") == "turn_context":
            active = p.get("turn_id") or active

    atoms = []
    seen = set()
    active = None
    had_prompt = False
    matched_humans = set()
    for row in rows:
        p = row.get("payload", {})
        kind = row.get("type")
        ts = parse_timestamp(row.get("timestamp"))
        if kind == "event_msg":
            if p.get("type") == "task_started":
                active = p.get("turn_id")
            elif p.get("type") == "turn_aborted":
                atoms.append(Atom("interrupt", timestamp=ts, turn_id=p.get("turn_id") or active))
            continue  # UI events and task_complete duplicate response_item
        if kind == "turn_context":
            active = p.get("turn_id") or active
            continue
        if kind == "compacted":
            if not had_prompt:
                print("warning: compaction before first prompt; earlier history may be missing", file=sys.stderr)
            continue
        if kind != "response_item":
            continue
        item_type = p.get("type")
        metadata = p.get("internal_chat_message_metadata_passthrough") or {}
        turn = metadata.get("turn_id") or active
        identity = p.get("call_id") if item_type in ("function_call", "custom_tool_call") else p.get("id")
        if identity:
            key = (item_type, identity)
            if key in seen:
                continue
            seen.add(key)
        if item_type == "message":
            role = p.get("role")
            if role not in ("user", "assistant"):
                continue
            if role == "assistant" and p.get("channel") not in (None, "final", "commentary"):
                continue
            text = content_text(p.get("content", []))
            if role == "user":
                if turn in humans:
                    # Events authorize prompt identity; preserve the canonical
                    # response text including attachment references and markup.
                    matches = [h for h in humans[turn] if text.strip() == h.strip() or (h.strip() and text.startswith(h + "\n[Image:"))]
                    if not matches:
                        if not legacy_prompt(text):
                            continue
                        print("warning: user context without matching human event skipped", file=sys.stderr)
                        continue
                    matched_humans.update((turn, h.strip()) for h in matches)
                else:
                    text = legacy_prompt(text)
                had_prompt = had_prompt or bool(text)
            if text.strip():
                atoms.append(Atom("prompt" if role == "user" else "response", text=text, timestamp=ts, turn_id=turn))
        elif item_type in ("function_call", "custom_tool_call"):
            raw = p.get("arguments", "") if item_type == "function_call" else p.get("input", "")
            if item_type == "function_call" and isinstance(raw, str):
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"arguments": raw}
            else:
                data = {"input": raw}
            if not isinstance(data, dict):
                data = {"arguments": data}
            atoms.append(Atom("tool_call", tool_name=p.get("name", "unknown"), tool_input=data, timestamp=ts, turn_id=turn))
        # reasoning, tool outputs, context and compaction are not rendered.
    if humans and not any(a.kind == "prompt" for a in atoms):
        raise ValueError("human events exist but no canonical prompts matched; unsupported log shape")
    missing = {(turn, h.strip()) for turn, texts in humans.items() for h in texts if h.strip()} - matched_humans
    if missing:
        raise ValueError(f"{len(missing)} human event(s) have no matching canonical prompt; unsupported or incomplete log")
    return atoms
