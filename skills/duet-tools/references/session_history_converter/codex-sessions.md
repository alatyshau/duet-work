# Local ChatGPT Code / Work and Codex sessions

Read this for a local session, including a chat called “Code” or “Work” in
the UI. Those names do not imply a different storage format: the app may
report the backing task as `kind: codex`. Do not argue about its UI mode
from that internal field. Conversely, not every cloud ChatGPT conversation
has a local rollout: this procedure requires an actual local session file.

## Find first, save only when requested

Run from this skill's folder, using `uv run --script` as usual:

```bash
uv run --script scripts/session_history_converter/save_codex_session.py --title "Проверь памятки по контракту"
uv run --script scripts/session_history_converter/save_codex_session.py --session <UUID-or-prefix>
uv run --script scripts/session_history_converter/save_codex_session.py <workspace-folder>
```

These commands only list matches. The optional `--codex-home <folder>`
overrides `$CODEX_HOME`, otherwise `~/.codex`. Discovery searches both
`sessions/` (normally `YYYY/MM/DD/rollout-…-<UUID>.jsonl`) and
`archived_sessions/`, confirming identity and workspace from `session_meta`.
A workspace filter is an exact match of the recorded `cwd`, not an assumed
relationship to the business where the chat's documents now live.

The title is separate from the transcript. Read-only local lookup uses
`session_index.jsonl` and the newest readable `state_*.sqlite` database's
`threads` table. On newer schemas the display title is `name`, while
`title` can contain the entire initial prompt. Older schemas may have only
`title`. These are implementation details, not a stable public API.

If a title is missing or outdated, use the app's `list_threads` tool when
available and confirm its UUID against the local file. `read_thread` can
help identify a conversation, but its paginated/truncated result is not a
full export. Without those tools, list by workspace or use a known UUID.
Never pick the newest chat merely because the requested title is absent.
A duplicate title, ambiguous UUID prefix, or multiple copies requires
selection, not merging histories. If no local file exists, say so and use
the browser-export guide only for an actual browser/cloud export request.

## Save through the shared layout

```bash
uv run --script scripts/session_history_converter/save_codex_session.py \
  --session <UUID> --dest <parent-dir> --name <Name> --client ChatGPTWork
```

Use `ChatGPTCode` or `ChatGPTWork` only when the person or UI establishes
that label; the neutral default is `Codex`, with the actual model recorded
separately in `INDEX.md`. The timestamp comes from the first human prompt,
converted to this machine's local time, not the rollout filename or last
activity. An explicit `--session latest` is available for a workspace;
otherwise saving requires exactly one match.

Output uses the same folder and turn format as Claude Code:

```text
<dest>/<YYMMDD>_<HHMM>_<Client>_<Name>/
    rollout-….jsonl
    01_MMDD_HHMM.md
    02_MMDD_HHMM.md
    …
```

The saver snapshots the source outside the workspace, then parses and
archives those same bytes. Prefer a completed, idle session; a live session
is only a point-in-time snapshot. Invalid or truncated JSON aborts instead
of silently dropping messages. Repeating the same save refreshes turn files
and the raw snapshot, leaves `INDEX.md` alone, and reports stale turn files
without deleting them. Different sessions must use different folder names.
Do not run `convert.py` in the client's live sessions directory: it writes
next to its input. For an already copied rollout, generic `save.py` and
`convert.py` also recognize this source.

## What is preserved

The canonical stream is `response_item`: user messages, visible assistant
messages (including commentary), function calls with parsed arguments, and
custom tool calls with their raw input. These feed the shared `Atom` model,
renderer and heading normalization; one output file represents one turn,
with inline prompts and intermediate responses where present.

When available, `event_msg` human messages identify genuine user input;
other user-role context is not automatically a human prompt. Legacy logs
without those events use conservative leading-envelope cleanup, so inspect
the first turn for leaked harness context. Do not remove arbitrary XML from
inside the user's prose or code. Explicit turn IDs preserve interrupted
turn boundaries and steering messages; older logs without IDs use the same
response/prompt grouping heuristic as other sources.

Do not render `event_msg.item_completed`, `task_complete.last_agent_message`
or `compacted.replacement_history` again: they repeat messages or substitute
a summary for the model's context. Reasoning, hidden analysis, tool results,
system/developer instructions and environment metadata do not enter the
turn Markdown. Identical text in two genuine messages is still two
messages; only repeated record IDs are deduplicated. Logs with rollback
currently stop with an explicit unsupported-branch error; event-only logs
without canonical prompts also stop rather than produce a false transcript.

The **raw JSONL copy is unfiltered** and may contain private instructions,
tool results and reasoning records. This follows the existing Claude Code
archive layout; the clean Markdown is not a sanitization of that archive.
Neither source file is modified. Image content receives a reference/marker,
not inline base64; unknown media gets a warning and placeholder. Referenced
PDFs, images, generated documents and external URLs are not copied or
fetched, and client-specific citation markup remains as in the source.

## Verify and describe the saved chat

Compare genuine prompts and visible assistant messages with the source,
check the first and final turn, and verify that compaction did not introduce
a summary or duplicate. Check warnings rather than treating successful file
creation as proof of completeness. The parser is based on observed local
rollouts, not a guarantee for every historical/future client schema.

Write `INDEX.md` using the shared guide: the original title, what the chat
is about, export date, `client`, `session`, `session-started` with timezone,
and model (or models, if it changed). Explain that attachments are references
and the JSONL is the raw snapshot. Do not invent a public chat URL. Keep
personal examples and real transcripts out of the skill's Git repository;
regression fixtures use synthetic conversations.
