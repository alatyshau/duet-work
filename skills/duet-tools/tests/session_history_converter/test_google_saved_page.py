"""What the google_saved_page fixtures can't show: the slim copy that
slim_google_page.py keeps must convert exactly like the full page, and the
date it pins must win over the saved-from anchor."""

from datetime import date
from pathlib import Path

import pytest

from sources.google_saved_page import load_atoms, parse_clock, slim

CASES = sorted((Path(__file__).parent / "fixtures" / "google_saved_page").glob("*/input.html"))


def atoms_of(text: str, tmp_path: Path, name: str):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return [(a.kind, a.text, a.timestamp) for a in load_atoms(path)]


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.parent.name)
def test_slim_copy_converts_like_the_full_page(case: Path, tmp_path: Path):
    full = case.read_text(encoding="utf-8")
    assert atoms_of(slim(full), tmp_path, "slim.html") == atoms_of(full, tmp_path, "full.html")


@pytest.mark.parametrize("case", CASES, ids=lambda p: p.parent.name)
def test_slimming_twice_changes_nothing(case: Path):
    once = slim(case.read_text(encoding="utf-8"))
    assert slim(once) == once


def test_pinned_date_wins_over_the_saved_from_anchor(tmp_path: Path):
    full = CASES[0].read_text(encoding="utf-8")
    stamps = [t for _, _, t in atoms_of(slim(full, date(2026, 1, 2)), tmp_path, "slim.html") if t]
    assert stamps and all(t.date() == date(2026, 1, 2) for t in stamps)


@pytest.mark.parametrize(
    "label, clock",
    [("3:53 p.m.", (15, 53)), ("12:05 p.m.", (12, 5)), ("12:05 a.m.", (0, 5)), ("3:53 PM", (15, 53)), ("15:53", (15, 53))],
)
def test_clock_labels_in_any_locale(label: str, clock: tuple[int, int]):
    assert parse_clock(label) == clock
