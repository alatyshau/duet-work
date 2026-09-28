"""saving.py and save.py: the folder every source is saved into, and the
generic entry point that gets there from any export convert.py recognizes."""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from saving import folder_name, save_as_folder
from sources import claude_export

CONVERTER_DIR = Path(__file__).resolve().parents[2] / "scripts" / "session_history_converter"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_folder_name_is_start_client_name():
    start = datetime(2026, 9, 27, 1, 53, tzinfo=timezone.utc)
    assert folder_name(start, "ClaudeCodeFable", "РаботаНадФормами") == "260927_0153_ClaudeCodeFable_РаботаНадФормами"
    assert folder_name(start, "GoogleAI", "Эталоны", date_only=True) == "260927_GoogleAI_Эталоны"


def test_folder_name_needs_a_start():
    with pytest.raises(ValueError):
        folder_name(None, "Claude", "x")


def test_save_as_folder_copies_source_and_writes_turns(tmp_path: Path):
    source = FIXTURES_DIR / "claude_export" / "basic" / "input.md"
    atoms = claude_export.load_atoms(source)
    out_dir = save_as_folder(source, atoms, tmp_path / "source", "ClaudeChat", "Столицы")
    assert out_dir == tmp_path / "source" / "260915_1131_ClaudeChat_Столицы"  # first timestamp in the export
    assert sorted(p.name for p in out_dir.iterdir()) == ["01_0915_1131.md", "input.md"]


def _run_save(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CONVERTER_DIR / "save.py"), *args], capture_output=True, text=True)


def test_save_py_names_the_client_after_the_source(tmp_path: Path):
    source = FIXTURES_DIR / "claude_export" / "basic" / "input.md"
    result = _run_save(str(source), "--dest", str(tmp_path), "--name", "Столицы")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "260915_1131_ClaudeChat_Столицы" / "01_0915_1131.md").is_file()
    assert result.stdout.strip() == f"1 turns -> {tmp_path / '260915_1131_ClaudeChat_Столицы'}"


def test_save_py_refuses_an_undated_source_without_start(tmp_path: Path):
    source = FIXTURES_DIR / "google_export" / "basic" / "input.md"
    result = _run_save(str(source), "--dest", str(tmp_path), "--name", "Эталоны")
    assert result.returncode != 0
    assert "--start" in result.stderr


def test_save_py_dates_an_undated_source_from_start(tmp_path: Path):
    source = FIXTURES_DIR / "google_export" / "basic" / "input.md"
    result = _run_save(str(source), "--dest", str(tmp_path), "--name", "Эталоны", "--start", "260926")
    assert result.returncode == 0, result.stderr
    out_dir = tmp_path / "260926_GoogleAI_Эталоны"
    assert sorted(p.name for p in out_dir.iterdir()) == ["01.md", "02.md", "input.md"]
