#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Slims a Google AI Mode page saved from Chrome ("Save Page As → Web Page,
Complete") down to what convert.py reads from it, and writes the result into
the chat's folder — the copy that is kept, so the turns can be rebuilt later.

A saved page is ~18 MB, of which the conversation's text is under half a
megabyte: the rest is stylesheets, scripts, icons, UI widgets, and the side
panel with the viewer's whole search history, none of which belongs on a
synced drive. What stays: each turn's prompt, its time, the response
markup, the formulas (MathML and glyphs), the citation links, the page title
and Chrome's saved-from comment, which dates the turns — see
sources/google_saved_page.py. Converting the slim copy gives the same turn
files as converting the full page.

Usage: uv run --script slim_google_page.py <saved-page.html> <chat-folder> [--date YYYY-MM-DD]

A prompt the page labels with its day is dated by that label. One labeled
only with a time needs its day from elsewhere: --date pins the day of the
first such prompt; without it, that day is the one on which Google issued
the page its token, which is right only if the chat began that day. The
script prints what it assumed so the agent can confirm it — the steps are
in references/session_history_converter/google-ai-mode.md. The slim copy is written as
<chat-folder>/<saved-page name>; the '_files' folder Chrome saves next to
the page is not needed and is not read.
"""

import sys
from datetime import date, datetime
from pathlib import Path

sys.dont_write_bytecode = True  # must come before importing sibling modules,
sys.path.insert(0, str(Path(__file__).parent))  # or __pycache__ ends up on the synced drive

from sources.google_saved_page import find_turns, first_turn_date, parse_html, pinned_date, slim, token_issued_at, turn_clock, turn_day, turn_stamps  # noqa: E402


def shown(stamp: date) -> str:
    return f"{stamp:%Y-%m-%d %H:%M}" if isinstance(stamp, datetime) else f"{stamp:%Y-%m-%d}"


def day_of(stamp: date) -> date:
    return stamp.date() if isinstance(stamp, datetime) else stamp


def main() -> None:
    args = sys.argv[1:]
    pinned = None
    if "--date" in args:
        i = args.index("--date")
        pinned = date.fromisoformat(args[i + 1])
        del args[i : i + 2]
    if len(args) != 2:
        sys.exit("usage: slim_google_page.py <saved-page.html> <chat-folder> [--date YYYY-MM-DD]")

    source, folder = Path(args[0]), Path(args[1])
    text = source.read_text(encoding="utf-8")
    turns = find_turns(parse_html(text))
    if not turns:
        sys.exit(f"no AI Mode turns in {source} — saved as 'HTML Only' instead of 'Web Page, Complete'?")
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / source.name
    slimmed = slim(text, pinned)
    out.write_text(slimmed, encoding="utf-8")
    print(f"{source.stat().st_size / 1e6:.1f} MB -> {len(slimmed.encode()) / 1e6:.2f} MB: {out}")

    issued, start = token_issued_at(text), first_turn_date(slimmed)
    timed = sum(turn_day(t) is None and turn_clock(t) is not None for t in turns)  # prompts whose label shows only a time
    if timed and issued is not None:
        print(f"Google issued the page its token on {issued:%Y-%m-%d at %H:%M}")
    if timed and start is None:
        print("no date on the page: ask when the chat began and rerun with --date YYYY-MM-DD", file=sys.stderr)
        return
    stamps = [s for s in turn_stamps(turns, start) if s]
    if stamps:
        print(f"{len(turns)} prompts dated {shown(stamps[0])} .. {shown(stamps[-1])}")
        days = (day_of(stamps[-1]) - day_of(stamps[0])).days + 1
        print(f"the chat spans {days} day{'s' if days > 1 else ''}")
    if not timed:
        if stamps:
            print("every prompt carries its own day on the page — nothing to confirm")
        return
    if pinned_date(slimmed) is not None:
        print(f"the first prompt labeled with a time is pinned to {start}")
    else:
        print(f"assumed: the first prompt labeled with a time was asked on {start}, the day Google issued the page its token — confirm it, or rerun with --date")


if __name__ == "__main__":
    main()
