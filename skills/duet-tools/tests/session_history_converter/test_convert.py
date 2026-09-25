"""The one behavior of convert.py that a fixture can't show: what it says
about files it did not write."""

from pathlib import Path

from convert import stale_turn_files


def test_stale_turn_files_reports_only_leftover_turn_files(tmp_path: Path):
    for name in ["01_0101_1000.md", "02_0101_1001.md", "03.md", "notes.md", "input.jsonl"]:
        (tmp_path / name).write_text("", encoding="utf-8")
    assert stale_turn_files(tmp_path, {"01_0101_1000.md"}) == ["02_0101_1001.md", "03.md"]


def test_no_stale_files_when_everything_was_rewritten(tmp_path: Path):
    (tmp_path / "01.md").write_text("", encoding="utf-8")
    assert stale_turn_files(tmp_path, {"01.md"}) == []
