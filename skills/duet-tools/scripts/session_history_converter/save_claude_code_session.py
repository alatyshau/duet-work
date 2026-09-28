#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Finds Claude Code sessions for a workspace folder and saves one of them
as a folder of its own in our layout, under a directory the person names — the steps that otherwise have to be done
by hand every time a conversation is worth keeping:

1. Work out which `~/.claude/projects/<dir>/` holds the sessions of a given
   workspace folder. Claude Code names that directory after the folder's
   absolute path with every character outside [A-Za-z0-9] replaced by `-`,
   so a path with non-Latin segments turns into a run of dashes and several
   different folders can share one directory name. The `cwd` recorded in
   each session is therefore the real test of which folder a session
   belongs to, and the directory name is only where to look.
2. Read each session's start (first human prompt, in local time — see
   sources/claude_jsonl.parse_timestamp for why local), its length, the
   model that answered, and the first prompt, so the right one can be
   picked without opening 8 MB of JSON.
3. Hand the chosen session to saving.py, which creates
   `<dest>/<YYMMDD>_<HHMM>_<Client>_<Name>/`, copies the session file in
   and splits it into turn files — the same layout every source gets via
   save.py. The start time is the session's first human prompt, local
   time; `<Client>` defaults to "ClaudeCode" plus the model family
   ("ClaudeCodeFable" for claude-fable-*, "ClaudeCodeOpus", ...).

Usage:

    uv run --script save_claude_code_session.py [<workspace-folder>]
        list the sessions of that folder (default: the current directory)

    uv run --script save_claude_code_session.py <workspace-folder> --dest <parent-dir> --name <Name> [--session <id>|latest] [--client <Label>]
        save one session (default: the most recently started) under <parent-dir>

<workspace-folder> may be a sub-folder of the one the session was started
in: the search walks up until a projects directory exists, and sessions are
then matched by their recorded cwd against that ancestor.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True  # must come before importing sibling modules,
sys.path.insert(0, str(Path(__file__).parent))  # or __pycache__ ends up on the synced drive

from saving import save_as_folder  # noqa: E402
from sources import claude_jsonl  # noqa: E402

PROJECTS_ROOT = Path.home() / ".claude" / "projects"
MODEL_FAMILY_RE = re.compile(r"^claude-([a-z]+)")


def project_dir_name(folder: Path) -> str:
    """The name Claude Code gives the projects directory of a workspace folder."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(folder))


def client_label(model: str | None) -> str:
    """"ClaudeCodeFable" for "claude-fable-5-1"; plain "ClaudeCode" when the
    model is unknown or not of the claude-<family>-... shape."""
    m = MODEL_FAMILY_RE.match(model or "")
    return "ClaudeCode" + (m.group(1).capitalize() if m else "")


@dataclass
class SessionInfo:
    path: Path
    session_id: str
    cwd: str | None
    start: datetime | None  # first human prompt, local time
    end: datetime | None  # last record of any kind, local time
    prompts: int  # human prompts
    model: str | None
    first_prompt: str


def scan_session(path: Path) -> SessionInfo:
    """A light pass over one session file: only the fields the listing and
    the folder name need, without building atoms for every record."""
    cwd = start = end = model = None
    prompts = 0
    first_prompt = ""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = claude_jsonl.parse_timestamp(record.get("timestamp"))
            if ts:
                end = ts
            if cwd is None and record.get("cwd"):
                cwd = record["cwd"]
            msg = record.get("message")
            if not isinstance(msg, dict):
                continue
            origin = record.get("origin")
            if msg.get("role") == "user" and isinstance(origin, dict) and origin.get("kind") == "human":
                text = _prompt_text(msg.get("content"))
                if text:
                    prompts += 1
                    if start is None:
                        start = ts
                        first_prompt = text
            elif msg.get("role") == "assistant" and model is None and msg.get("model"):
                model = msg["model"]
    return SessionInfo(path, path.stem, cwd, start, end, prompts, model, first_prompt)


def _prompt_text(content) -> str:
    if isinstance(content, str):
        return claude_jsonl.clean_prompt_text(content)
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return claude_jsonl.clean_prompt_text("\n".join(parts))
    return ""


def find_project_dir(folder: Path, projects_root: Path = PROJECTS_ROOT) -> tuple[Path, Path]:
    """(projects directory, the workspace ancestor it was named after).
    Walks up from `folder` because a session is filed under the folder the
    client was started in, and the person may be asking from deeper down."""
    folder = folder.resolve()
    for candidate in [folder, *folder.parents]:
        project_dir = projects_root / project_dir_name(candidate)
        if project_dir.is_dir():
            return project_dir, candidate
    sys.exit(f"no Claude Code sessions found for {folder} (looked under {projects_root})")


def sessions_for(folder: Path, projects_root: Path = PROJECTS_ROOT) -> list[SessionInfo]:
    """Sessions of `folder`, newest start first. Only sessions whose recorded
    cwd is the matched ancestor or somewhere beneath it count: the directory
    name alone can't tell folders apart once their paths collapse to dashes."""
    project_dir, root = find_project_dir(folder, projects_root)
    found = []
    for path in project_dir.glob("*.jsonl"):
        info = scan_session(path)
        if info.cwd is None or not info.prompts:
            continue
        if Path(info.cwd) == root or root in Path(info.cwd).parents:
            found.append(info)
    found.sort(key=lambda s: s.start or datetime.min.replace(tzinfo=None), reverse=True)
    return found


def format_listing(sessions: list[SessionInfo]) -> str:
    if not sessions:
        return "no sessions with a human prompt"
    lines = []
    for s in sessions:
        start = f"{s.start:%Y-%m-%d %H:%M}" if s.start else "?"
        end = f"{s.end:%H:%M}" if s.end else "?"
        snippet = s.first_prompt.replace("\n", " ")
        if len(snippet) > 70:
            snippet = snippet[:69] + "…"
        size_mb = s.path.stat().st_size / 1_000_000
        lines.append(f"{s.session_id}  {start}–{end}  {s.prompts:3d} prompts  {client_label(s.model):16s} {size_mb:5.1f} MB  {snippet}")
    return "\n".join(lines)


def save_session(info: SessionInfo, dest: Path, name: str, client: str | None = None) -> Path:
    if info.start is None:
        sys.exit(f"session {info.session_id} has no human prompt to date it by")
    atoms = claude_jsonl.load_atoms(info.path)
    return save_as_folder(info.path, atoms, dest, client or client_label(info.model), name, info.start)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", nargs="?", default=".", help="workspace folder (default: current directory)")
    ap.add_argument("--dest", type=Path, help="where to create the chat's folder (the person's choice); with --name, saves")
    ap.add_argument("--name", help="the <Name> part of <YYMMDD>_<HHMM>_<Client>_<Name>")
    ap.add_argument("--session", default="latest", help="session id (prefix is enough) or 'latest' (default)")
    ap.add_argument("--client", help="override the <Client> part (default: ClaudeCode + model family)")
    args = ap.parse_args()

    sessions = sessions_for(Path(args.folder))
    if not (args.dest and args.name):
        if args.dest or args.name:
            sys.exit("saving needs both --dest and --name")
        print(format_listing(sessions))
        return

    if args.session == "latest":
        chosen = sessions[0] if sessions else None
    else:
        matches = [s for s in sessions if s.session_id.startswith(args.session)]
        if len(matches) > 1:
            sys.exit(f"ambiguous session prefix {args.session!r}: " + ", ".join(s.session_id for s in matches))
        chosen = matches[0] if matches else None
    if chosen is None:
        sys.exit("no matching session")

    out_dir = save_session(chosen, args.dest, args.name, args.client)
    turn_files = sorted(p.name for p in out_dir.iterdir() if p.suffix == ".md")
    print(f"{len(turn_files)} turns -> {out_dir}")


if __name__ == "__main__":
    main()
