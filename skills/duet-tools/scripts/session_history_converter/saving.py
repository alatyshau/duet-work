"""Saving a conversation as a folder of its own in our layout — the part that
is the same for every source, so it lives here and not in any one entry
script:

    <dest>/<YYMMDD>_<HHMM>_<Client>_<Name>/
        <the source file, copied in as it was>
        01_MMDD_HHMM.md, 02_..., one turn file per human prompt

`<YYMMDD>_<HHMM>` is when the conversation started, `<Client>` names what
answered (ClaudeCodeFable, ClaudeChat, GoogleAI, DeepSeek), `<Name>` is the
person's own title for it; `<dest>`, where the folder goes, is the
person's choice too. A source that carries no timestamps gets only
`<YYMMDD>` in the folder name, and the person has to supply that date.
"""

import shutil
from datetime import datetime
from pathlib import Path

from turns import Atom, render_turn, split_turns, turn_filename


def folder_name(start: datetime | None, client: str, name: str, date_only: bool = False) -> str:
    if start is None:
        raise ValueError("a start time is needed to name the folder")
    stamp = f"{start:%y%m%d}" if date_only else f"{start:%y%m%d_%H%M}"
    return f"{stamp}_{client}_{name}"


def first_timestamp(atoms: list[Atom]) -> datetime | None:
    return next((a.timestamp for a in atoms if a.timestamp), None)


def save_as_folder(source_path: Path, atoms: list[Atom], dest: Path, client: str, name: str, start: datetime | None = None, date_only: bool = False) -> Path:
    """Creates the folder, copies the source in, writes the turn files.
    `start` defaults to the first timestamp in the conversation. An existing
    folder is reused, so re-running after more turns arrived refreshes the
    same place; turn files from an earlier, longer run are not deleted."""
    start = start or first_timestamp(atoms)
    out_dir = dest / folder_name(start, client, name, date_only)
    out_dir.mkdir(parents=True, exist_ok=True)
    copied = out_dir / source_path.name
    if source_path.resolve() != copied.resolve():
        shutil.copyfile(source_path, copied)
    for n, turn_atoms in enumerate(split_turns(atoms), start=1):
        (out_dir / turn_filename(n, turn_atoms)).write_text(render_turn(n, turn_atoms), encoding="utf-8")
    return out_dir
