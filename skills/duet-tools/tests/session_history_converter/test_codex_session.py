import json
import sqlite3
from pathlib import Path

import pytest

from convert import load_atoms
from save import default_client, detect_source
from save_codex_session import find_sessions, save_session, scan_session, title_index
from sources import claude_jsonl, codex_jsonl
from turns import split_turns

FIXTURE = Path(__file__).parent / 'fixtures/codex_jsonl/basic/input.jsonl'


def write_log(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    return path


def row(kind, payload):
    return {'type': kind, 'timestamp': '2026-09-03T07:00:00Z', 'payload': payload}


def message(role, text, **extra):
    return row('response_item', dict(type='message', role=role, content=[{'type': 'input_text', 'text': text}], **extra))


def test_detection_and_repeated_prompts():
    assert codex_jsonl.detect(FIXTURE)
    assert not claude_jsonl.detect(FIXTURE)
    assert default_client(detect_source(FIXTURE), FIXTURE) == 'Codex'
    atoms = load_atoms(FIXTURE)
    assert len(split_turns(atoms)) == 3
    assert [a.text for a in atoms if a.kind == 'prompt'].count('Проверь памятку.') == 2


def test_legacy_envelopes_and_quoted_markup(tmp_path):
    path = write_log(tmp_path/'old.jsonl', [
        row('session_meta', {'id': 'old'}),
        message('user', '<environment_context>context</environment_context>\nHello'),
        message('assistant', 'answer'),
        message('user', 'Explain this:\n```xml\n<environment_context>keep</environment_context>\n```'),
        message('assistant', 'not visible', channel='analysis'),
    ])
    atoms = load_atoms(path)
    assert atoms[0].text == 'Hello'
    assert 'keep</environment_context>' in atoms[-1].text
    assert len(atoms) == 3


def test_malformed_snapshot_and_rollback_fail_closed(tmp_path):
    path = tmp_path/'broken.jsonl'
    path.write_text(FIXTURE.read_text() + '{"type":')
    with pytest.raises(ValueError, match='invalid JSON'):
        load_atoms(path)
    write_log(path, [row('session_meta', {'id':'test'}), row('event_msg', {'type':'thread_rolled_back','num_turns':1})])
    with pytest.raises(ValueError, match='branch reconstruction'):
        load_atoms(path)


def test_image_and_unknown_content_markers(tmp_path):
    path = write_log(tmp_path/'image.jsonl', [row('session_meta', {'id':'test'}), row('response_item', {
        'type':'message', 'role':'user', 'content':[
            {'type':'input_image','image_url':'data:image/png;base64,PRIVATE'},
            {'type':'future_media'}]})])
    text = load_atoms(path)[0].text
    assert 'embedded image' in text and 'future_media' in text
    assert 'PRIVATE' not in text


def test_title_index_workspace_archive_and_snapshot(tmp_path):
    home = tmp_path/'home'
    source = home/'archived_sessions'/'rollout-test-session.jsonl'
    source.parent.mkdir(parents=True)
    source.write_bytes(FIXTURE.read_bytes())
    (home/'session_index.jsonl').write_text(json.dumps({'id':'test-session','thread_name':'Old name'})+'\n')
    con = sqlite3.connect(home/'state_5.sqlite')
    con.execute('CREATE TABLE threads (id TEXT, title TEXT, name TEXT)')
    con.execute('INSERT INTO threads VALUES (?, ?, ?)', ('test-session','Initial prompt','Проверь памятки'))
    con.commit(); con.close()
    before = source.read_bytes()
    assert title_index(home)['test-session'] == 'Проверь памятки'
    assert not find_sessions(home, folder=Path('/different'))
    found = find_sessions(home, title='ПАМЯТКИ')
    assert len(found) == 1 and found[0].prompts == 4
    assert find_sessions(home, session='test-')[0].models == ['test-model']
    out = save_session(found[0], tmp_path/'dest', 'Sample', 'ChatGPTWork')
    assert out.name == '260903_0700_ChatGPTWork_Sample'
    assert (out/source.name).read_bytes() == before == source.read_bytes()
    assert len(list(out.glob('*.md'))) == 3
    index = out/'INDEX.md'; index.write_text('user index')
    save_session(found[0], tmp_path/'dest', 'Sample', 'ChatGPTWork')
    assert index.read_text() == 'user index'
    for expected in (FIXTURE.parent/'expected').iterdir():
        assert (out/expected.name).read_text() == expected.read_text()
    with pytest.raises(ValueError, match='folder labels'):
        save_session(found[0], tmp_path/'dest', '../escape')


def test_unknown_jsonl_not_claimed(tmp_path):
    path = write_log(tmp_path/'other.jsonl', [{'unrelated':'data'}])
    assert not codex_jsonl.detect(path)
    assert not claude_jsonl.detect(path)


def test_event_only_log_not_silently_exported(tmp_path):
    path = write_log(tmp_path/'events.jsonl', [row('session_meta', {'id':'test'}), row('event_msg', {'type':'user_message', 'message':'hello'})])
    with pytest.raises(ValueError, match='unsupported log shape'):
        load_atoms(path)
