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

--date pins the first prompt's date. Without it the first prompt is dated
the day the tab opened the thread, which is right only if the chat began
that day; the script prints what it assumed so the agent can confirm it —
the steps are in references/session_history_converter/google-ai-mode.md. The slim copy is written as
<chat-folder>/<saved-page name>; the '_files' folder Chrome saves next to
the page is not needed and is not read.
"""

import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True  # must come before importing sibling modules,
sys.path.insert(0, str(Path(__file__).parent))  # or __pycache__ ends up on the synced drive

from sources.google_saved_page import assign_dates, find_turns, first_turn_date, parse_html, pinned_date, slim, tab_opened_at, turn_clock  # noqa: E402


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

    opened, start = tab_opened_at(text), first_turn_date(slimmed)
    if opened is not None:
        print(f"the tab opened this thread on {opened:%Y-%m-%d at %H:%M}")
    if start is None:
        print("no date on the page: ask when the chat began and rerun with --date YYYY-MM-DD", file=sys.stderr)
        return
    stamps = [s for s in assign_dates([turn_clock(t) for t in turns], start) if s]
    if stamps:
        print(f"{len(turns)} prompts dated {stamps[0]:%Y-%m-%d %H:%M} .. {stamps[-1]:%Y-%m-%d %H:%M}")
        days = (stamps[-1].date() - stamps[0].date()).days + 1
        print(f"the chat spans {days} day{'s' if days > 1 else ''}")
    if pinned_date(slimmed) is not None:
        print(f"first prompt's date pinned to {start}")
    else:
        print(f"assumed: the first prompt was asked on {start}, the day the tab opened the thread — confirm it, or rerun with --date")


if __name__ == "__main__":
    main()
