#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Saves one exported conversation — any source convert.py understands — as
a folder of its own in our layout (see saving.py for the shape), under
whatever directory the person names with --dest:

    uv run --script save.py <path-to-source> --dest <parent-dir> --name <Name> [--client <Label>] [--start YYMMDD[_HHMM]]

`<Client>` defaults to what the source is: ClaudeChat for a claude.ai export,
ChatGPT for a chatgpt.com export, Gemini for a gemini.google.com export,
GoogleAI for a Google AI Mode export or saved page, DeepSeek for a DeepSeek
export, ClaudeCode plus the model family for a Claude Code session, Codex
for a local Codex / ChatGPT Code/Work session. The
start time is the first timestamp in the conversation; a source without
timestamps (Google AI Mode exports carry none) needs `--start`, and then the
folder is named by date alone unless an hour is given.

For a Claude Code session that still has to be found on this machine, use
save_claude_code_session.py instead — it lists the sessions of a workspace
folder and ends up here.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True  # must come before importing sibling modules,
sys.path.insert(0, str(Path(__file__).parent))  # or __pycache__ ends up on the synced drive

import convert  # noqa: E402
from saving import first_timestamp, save_as_folder  # noqa: E402

CLIENT_BY_SOURCE = {
    "codex_jsonl": "Codex",
    "claude_export": "ClaudeChat",
    "chatgpt_export": "ChatGPT",
    "gemini_export": "Gemini",
    "google_export": "GoogleAI",
    "google_saved_page": "GoogleAI",
    "deepseek_export": "DeepSeek",
}


def detect_source(path: Path):
    for source in convert.SOURCES:
        if source.detect(path):
            return source
    sys.exit(f"unrecognized source: {path}")


def default_client(source, path: Path) -> str:
    key = source.__name__.rsplit(".", 1)[-1]
    if key == "claude_jsonl":
        from save_claude_code_session import client_label, scan_session

        return client_label(scan_session(path).model)
    return CLIENT_BY_SOURCE.get(key, key)


def parse_start(raw: str) -> tuple[datetime, bool]:
    """'YYMMDD' or 'YYMMDD_HHMM' -> (datetime, date_only)."""
    for fmt, date_only in (("%y%m%d_%H%M", False), ("%y%m%d", True)):
        try:
            return datetime.strptime(raw, fmt), date_only
        except ValueError:
            continue
    sys.exit(f"--start must be YYMMDD or YYMMDD_HHMM, got {raw!r}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("source", type=Path, help="the exported conversation")
    ap.add_argument("--dest", type=Path, required=True, help="where to create the chat's folder — the person's choice")
    ap.add_argument("--name", required=True, help="the <Name> part of <YYMMDD>_<HHMM>_<Client>_<Name>")
    ap.add_argument("--client", help="override the <Client> part")
    ap.add_argument("--start", help="YYMMDD or YYMMDD_HHMM when the source carries no timestamps")
    args = ap.parse_args()
    if not args.source.is_file():
        sys.exit(f"no such file: {args.source}")

    source = detect_source(args.source)
    atoms = source.load_atoms(args.source)
    client = args.client or default_client(source, args.source)
    if args.start:
        start, date_only = parse_start(args.start)
    else:
        start, date_only = first_timestamp(atoms), False
        if start is None:
            sys.exit("this source carries no timestamps; give the start with --start YYMMDD[_HHMM]")

    out_dir = save_as_folder(args.source, atoms, args.dest, client, args.name, start, date_only)
    turn_files = sorted(p.name for p in out_dir.iterdir() if p.suffix == ".md" and p.name != args.source.name)
    print(f"{len(turn_files)} turns -> {out_dir}")


if __name__ == "__main__":
    main()
