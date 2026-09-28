"""save_claude_code_session.py: finding a workspace folder's sessions and naming the
saved folder. A synthetic projects root under tmp_path stands in for
~/.claude/projects, so nothing here depends on the machine's own sessions."""

import json
from pathlib import Path

from save_claude_code_session import (
    client_label,
    format_listing,
    project_dir_name,
    save_session,
    scan_session,
    sessions_for,
)


def test_project_dir_name_replaces_everything_but_ascii_alphanumerics():
    assert project_dir_name(Path("/Users/me/My Drive/!Лаб/x_y.z")) == "-Users-me-My-Drive------x-y-z"  # "!Лаб" is four characters, then "/"


def test_client_label_takes_the_model_family():
    assert client_label("claude-fable-5-1") == "ClaudeCodeFable"
    assert client_label("claude-opus-5-5") == "ClaudeCodeOpus"
    assert client_label(None) == "ClaudeCode"
    assert client_label("gpt-9") == "ClaudeCode"


def _write_session(path: Path, cwd: str, first_prompt: str, start: str, model: str = "claude-fable-5-1") -> None:
    records = [
        {"type": "queue-operation", "timestamp": start},
        {
            "type": "user",
            "cwd": cwd,
            "message": {"role": "user", "content": first_prompt},
            "timestamp": start,
            "origin": {"kind": "human"},
        },
        {
            "type": "assistant",
            "cwd": cwd,
            "message": {"role": "assistant", "model": model, "content": [{"type": "text", "text": "Done."}]},
            "timestamp": "2026-09-27T09:00:00.000Z",
        },
    ]
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")


def _projects_root(tmp_path: Path) -> tuple[Path, Path]:
    """Two workspace folders whose paths collapse to the same projects
    directory name (same length, non-Latin segments), one session each,
    plus a session with no human prompt that must be ignored."""
    workspace = tmp_path / "Диск" / "Физика"
    other = tmp_path / "Диск" / "Логика"  # same length as Физика -> same dashes
    assert project_dir_name(workspace) == project_dir_name(other)
    root = tmp_path / "projects"
    project_dir = root / project_dir_name(workspace)
    project_dir.mkdir(parents=True)
    _write_session(project_dir / "aaaa.jsonl", str(workspace), "первый вопрос", "2026-09-27T08:53:36.000Z")
    _write_session(project_dir / "bbbb.jsonl", str(other), "чужой вопрос", "2026-09-27T10:00:00.000Z")
    _write_session(project_dir / "cccc.jsonl", str(workspace), "старый вопрос", "2026-09-26T20:00:00.000Z", model="claude-opus-5-5")
    (project_dir / "dddd.jsonl").write_text(json.dumps({"type": "queue-operation", "timestamp": "2026-09-27T11:00:00.000Z"}) + "\n")
    return workspace, root


def test_sessions_are_matched_by_recorded_cwd_not_by_directory_name(tmp_path: Path):
    workspace, root = _projects_root(tmp_path)
    found = sessions_for(workspace, root)
    assert [s.session_id for s in found] == ["aaaa", "cccc"]  # newest start first; bbbb is another folder, dddd has no prompt


def test_a_subfolder_finds_the_sessions_of_its_workspace(tmp_path: Path):
    workspace, root = _projects_root(tmp_path)
    sub = workspace / "мир" / "формы"
    sub.mkdir(parents=True)
    assert [s.session_id for s in sessions_for(sub, root)] == ["aaaa", "cccc"]


def test_scan_reads_start_prompt_and_model(tmp_path: Path):
    workspace, root = _projects_root(tmp_path)
    info = scan_session(root / project_dir_name(workspace) / "aaaa.jsonl")
    assert info.first_prompt == "первый вопрос"
    assert info.prompts == 1
    assert info.model == "claude-fable-5-1"
    assert f"{info.start:%Y-%m-%d %H:%M}" == "2026-09-27 08:53"  # conftest pins TZ=UTC


def test_listing_shows_one_line_per_session(tmp_path: Path):
    workspace, root = _projects_root(tmp_path)
    lines = format_listing(sessions_for(workspace, root)).splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("aaaa  2026-09-27 08:53–09:00    1 prompts  ClaudeCodeFable")
    assert lines[0].endswith("первый вопрос")


def test_save_creates_the_named_folder_with_source_and_turns(tmp_path: Path):
    workspace, root = _projects_root(tmp_path)
    chosen = sessions_for(workspace, root)[0]
    out_dir = save_session(chosen, tmp_path / "source", "РаботаНадФормами")
    assert out_dir == tmp_path / "source" / "260927_0853_ClaudeCodeFable_РаботаНадФормами"
    assert sorted(p.name for p in out_dir.iterdir()) == ["01_0927_0853.md", "aaaa.jsonl"]
    assert "первый вопрос" in (out_dir / "01_0927_0853.md").read_text(encoding="utf-8")


def test_client_override(tmp_path: Path):
    workspace, root = _projects_root(tmp_path)
    chosen = sessions_for(workspace, root)[0]
    out_dir = save_session(chosen, tmp_path / "source", "Имя", client="ClaudeCode")
    assert out_dir.name == "260927_0853_ClaudeCode_Имя"
