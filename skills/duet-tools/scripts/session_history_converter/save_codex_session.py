#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Find and save local Codex / ChatGPT Code / Work sessions.

Without --dest/--name, list matches without writing. Search by workspace,
--session UUID (or unique prefix), or --title from the local title index.
--codex-home defaults to CODEX_HOME or ~/.codex. Both sessions and
archived_sessions are searched. UI mode cannot be inferred from the log:
use --client ChatGPTWork or ChatGPTCode when known; default is Codex.
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

from convert import stale_turn_files
from saving import first_timestamp, folder_name, save_as_folder
from sources import codex_jsonl
from turns import split_turns, turn_filename


@dataclass
class SessionInfo:
    path: Path
    session_id: str
    cwd: str | None
    title: str | None
    start: datetime | None
    models: list[str]
    prompts: int
    first_prompt: str


def title_index(home: Path) -> dict[str, str]:
    """Optional, read-only index. It supplies titles, never session content."""
    titles = {}
    index = home / "session_index.jsonl"
    if index.is_file():
        for row in codex_jsonl.records(index):
            sid = row.get("id") or row.get("session_id")
            title = row.get("thread_name") or row.get("title")
            if sid and title:
                titles[sid] = title
    databases = sorted(home.glob("state_*.sqlite"), key=lambda p: int(p.stem.split("_")[-1]) if p.stem.split("_")[-1].isdigit() else -1, reverse=True)
    for db in databases:
        try:
            connection = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
            try:
                columns = {r[1] for r in connection.execute("PRAGMA table_info(threads)")}
                query = "SELECT id, title, name FROM threads" if "name" in columns else "SELECT id, title, NULL FROM threads"
                for sid, title, name in connection.execute(query):
                    # New desktop schemas put the UI title in name; title
                    # may still contain the entire initial prompt.
                    label = name or titles.get(sid) or title
                    if label:
                        titles[sid] = label
            finally:
                connection.close()
            break
        except sqlite3.Error as exc:
            print(f"warning: cannot read title index {db.name}: {exc}", file=sys.stderr)
    return titles


def session_metadata(path: Path) -> dict:
    first = next(codex_jsonl.records(path), {})
    return first.get("payload", {}) if first.get("type") == "session_meta" else {}


def scan_session(path: Path, title: str | None = None) -> SessionInfo:
    meta = session_metadata(path)
    atoms = codex_jsonl.load_atoms(path)
    prompts = [a for a in atoms if a.kind == "prompt"]
    models = []
    for row in codex_jsonl.records(path):
        model = row.get("payload", {}).get("model") if row.get("type") == "turn_context" else None
        if model and model not in models:
            models.append(model)
    return SessionInfo(path, meta.get("id") or meta.get("session_id") or path.stem,
                       meta.get("cwd"), title, first_timestamp(prompts), models,
                       len(prompts), prompts[0].text if prompts else "")


def find_sessions(home: Path, folder: Path | None = None, session: str | None = None, title: str | None = None) -> list[SessionInfo]:
    titles = title_index(home)
    found = []
    for root in (home / "sessions", home / "archived_sessions"):
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.jsonl")):
            # UUID filename filtering avoids reading unrelated large sessions.
            if session and session != "latest" and session not in path.name:
                continue
            if title and not any(sid in path.name and title.casefold() in label.casefold() for sid, label in titles.items()):
                continue
            meta = session_metadata(path)
            sid = meta.get("id") or meta.get("session_id")
            if not sid:
                continue
            if session and session != "latest" and not sid.startswith(session):
                continue
            label = titles.get(sid)
            if title and (not label or title.casefold() not in label.casefold()):
                continue
            cwd = meta.get("cwd")
            if folder and (not cwd or Path(cwd).resolve() != folder.resolve()):
                continue
            info = scan_session(path, label)
            if info.prompts:
                found.append(info)
    return sorted(found, key=lambda s: s.start.timestamp() if s.start else float('-inf'), reverse=True)


def format_listing(sessions: list[SessionInfo]) -> str:
    if not sessions:
        return "no matching local sessions; titles may be absent from the local index (try a UUID or workspace)"
    return "\n".join(
        f"{s.session_id} | {s.start.isoformat() if s.start else '?'} | {s.prompts} prompts | "
        f"{', '.join(s.models) or '?'} | {(s.title or '(title unavailable)').replace(chr(10), ' ')[:160]}\n"
        f"  {s.path}\n  cwd: {s.cwd}\n  {s.first_prompt.replace(chr(10), ' ')[:160]}"
        for s in sessions)


def save_session(info: SessionInfo, dest: Path, name: str, client: str = "Codex") -> Path:
    for label in (name, client):
        if not label.strip() or label in (".", "..") or any(c in label for c in '/\\\0'):
            raise ValueError("name and client must be non-empty folder labels, not paths")
    # Snapshot once, then parse and copy the same bytes; do not render one
    # version of a running session and archive a later, different version.
    with tempfile.TemporaryDirectory(prefix="duet-codex-") as tmp:
        snapshot = Path(tmp) / info.path.name
        shutil.copyfile(info.path, snapshot)
        atoms = codex_jsonl.load_atoms(snapshot)
        start = first_timestamp([a for a in atoms if a.kind == "prompt"])
        if start is None:
            raise ValueError("session has no dated human prompt")
        target = dest / folder_name(start, client, name)
        if target.exists():
            for old in target.glob("*.jsonl"):
                metadata = session_metadata(old)
                if (metadata.get("id") or metadata.get("session_id")) != info.session_id:
                    raise ValueError(f"destination belongs to another session: {target}")
        out = save_as_folder(snapshot, atoms, dest, client, name, start)
        written = {turn_filename(n, turn) for n, turn in enumerate(split_turns(atoms), 1)}
        stale = stale_turn_files(out, written)
        if stale:
            print("warning: stale turn files retained: " + ", ".join(stale), file=sys.stderr)
        return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder", nargs="?", type=Path, help="exact recorded workspace; defaults to cwd unless a selector is given")
    ap.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"))
    ap.add_argument("--session", help="UUID or unique prefix; 'latest' requires a workspace")
    ap.add_argument("--title", help="case-insensitive title substring in the local index")
    ap.add_argument("--dest", type=Path)
    ap.add_argument("--name")
    ap.add_argument("--client", default="Codex", help="Codex, ChatGPTCode or ChatGPTWork (explicit UI label)")
    args = ap.parse_args()
    if bool(args.dest) != bool(args.name):
        ap.error("saving needs both --dest and --name")
    folder = args.folder
    if folder is None and not (args.title or (args.session and args.session != "latest")):
        folder = Path.cwd()
    try:
        sessions = find_sessions(args.codex_home.expanduser(), folder, args.session, args.title)
        if args.dest is None:
            print(format_listing(sessions))
            return
        if args.session == "latest" and folder is not None:
            sessions = sessions[:1]
        if len(sessions) != 1:
            ap.error(f"saving needs one unambiguous session, found {len(sessions)}; list first, then give --session UUID")
        out = save_session(sessions[0], args.dest, args.name, args.client)
        print(f"saved session {sessions[0].session_id} -> {out}")
    except (ValueError, OSError) as exc:
        ap.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
