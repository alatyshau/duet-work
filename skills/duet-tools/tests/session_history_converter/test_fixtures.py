"""Runs every case under fixtures/<source>/<case>/ through the real
conversion pipeline and compares the result against fixtures/<source>/<case>/expected/.

Each case's input.* and expected/*.md are meant to be read directly, not
just executed: opening a case's two files side by side shows exactly what
the tool does with that input, without reading any Python. Adding a new
behavior means adding a new case here, not a new assertion in code.
"""

from pathlib import Path

import pytest

from convert import load_atoms
from turns import render_turn, split_turns, turn_filename

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def discover_cases() -> list[Path]:
    cases = []
    for source_dir in sorted(p for p in FIXTURES_DIR.iterdir() if p.is_dir()):
        for case_dir in sorted(p for p in source_dir.iterdir() if p.is_dir()):
            if (case_dir / "expected").is_dir():
                cases.append(case_dir)
    return cases


def case_id(case_dir: Path) -> str:
    return f"{case_dir.parent.name}/{case_dir.name}"


@pytest.mark.parametrize("case_dir", discover_cases(), ids=case_id)
def test_fixture_produces_the_expected_turn_files(case_dir: Path, tmp_path: Path):
    input_files = [f for f in case_dir.iterdir() if f.name != "expected"]
    assert len(input_files) == 1, f"{case_dir} must contain exactly one input file"
    source_file = input_files[0]

    work_file = tmp_path / source_file.name
    work_file.write_text(source_file.read_text(encoding="utf-8"), encoding="utf-8")

    atoms = load_atoms(work_file)
    turns = split_turns(atoms)
    for n, turn_atoms in enumerate(turns, start=1):
        (tmp_path / turn_filename(n, turn_atoms)).write_text(render_turn(n, turn_atoms), encoding="utf-8")

    expected_dir = case_dir / "expected"
    expected_names = sorted(f.name for f in expected_dir.iterdir())
    actual_names = sorted(f.name for f in tmp_path.iterdir() if f.name != source_file.name)
    assert actual_names == expected_names, f"{case_id(case_dir)}: produced files don't match expected/"

    for name in expected_names:
        expected_text = (expected_dir / name).read_text(encoding="utf-8")
        actual_text = (tmp_path / name).read_text(encoding="utf-8")
        assert actual_text == expected_text, f"{case_id(case_dir)}/{name} doesn't match its expected content"
