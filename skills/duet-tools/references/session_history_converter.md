# Session History Converter

`scripts/session_history_converter/` turns an AI conversation into one
markdown file per human turn, `NN_MMDD_HHMM.md` (see `turns.py` and the
docstring of `convert.py` for the exact shape), and can file the whole
conversation as a folder of its own, under whatever directory the person
names with `--dest` (a context's `source/`, a work folder's `sample_chats/`,
anywhere):

    <dest>/<YYMMDD>_<HHMM>_<Client>_<Name>/
        <the source file, copied in as it was>
        01_MMDD_HHMM.md, 02_..., one file per human prompt

## Entry points

**Convert in place** — the turn files land next to the source file. For a
file that already sits where it belongs.

```bash
uv run --script scripts/session_history_converter/convert.py <path-to-source>
```

**Save an export as a folder** — any export `convert.py` recognizes.
`<Client>` follows the source (ClaudeChat, ChatGPT, Gemini, GoogleAI, DeepSeek, ClaudeCode plus
the model family, or Codex for a local Code/Work rollout); the start comes
from the first timestamp, or from
`--start YYMMDD[_HHMM]` when the export carries none (Google AI Mode
exports don't), and then the folder is named by date alone unless an hour
is given.

```bash
uv run --script scripts/session_history_converter/save.py <path-to-source> --dest <parent-dir> --name <Name> [--client <Label>] [--start YYMMDD[_HHMM]]
```

**Save a Claude Code session** — without `--dest`/`--name` it lists the sessions of
a workspace folder (start time, model, first prompt); with them it saves one,
the most recently started unless `--session` names another. `<HHMM>` is the
first human prompt in local time; `<Client>` defaults to `ClaudeCode` plus
the model family (`ClaudeCodeFable`, `ClaudeCodeOpus`). Re-running into the
same `--dest` and `--name` refreshes the same folder after more turns.

```bash
uv run --script scripts/session_history_converter/save_claude_code_session.py <workspace-folder>
uv run --script scripts/session_history_converter/save_claude_code_session.py <workspace-folder> --dest <parent-dir> --name <Name> [--session <id>|latest] [--client <Label>]
```

**Find or save a local ChatGPT Code / Work (Codex) session** — read
[session_history_converter/codex-sessions.md](session_history_converter/codex-sessions.md)
for title/UUID/workspace discovery, read-only analysis, export commands and
format limitations. This is the local-session route, not a Chrome exporter.
It uses the same folder and turn layout as Claude Code.

**A Google AI Mode page saved from Chrome** goes through a slim step first
and needs its dates confirmed — read
[session_history_converter/google-ai-mode.md](session_history_converter/google-ai-mode.md)
when handed one.

## The folder's INDEX.md

The scripts never write or touch `INDEX.md`; after saving, the agent writes
it. Frontmatter:

- `folder-type: ai-session`
- `client` — Claude Code, ChatGPT Code, ChatGPT Work, Codex, Claude Chat, ChatGPT, Gemini, Google AI Mode, DeepSeek
- `session-started` — when the session began
- `session` — a local Claude Code or Codex session's id
- `link` — the chat's URL, when the client has one
- `model` — when the source names it

Only the fields the source carries. Below the frontmatter: a title, a
paragraph **Что это**, a section **## Что сделано** with dated entries. What
goes into them is for the agent to decide from the context it has.

## Layout (for changing the tool)

The output format is a growing part of the tool itself, not of any one
source, so it lives in shared modules and each source only feeds them:

- `turns.py` — the shared model and renderer. Every source reduces its
  input to this shape; the format itself lives only here.
- `saving.py` — the saved-chat folder layout, `<YYMMDD>_<HHMM>_<Client>_<Name>/`
  with the export copied in and the turn files beside it. Shared by the
  entry points below so the layout is defined once.
- `save.py` — saves any export convert.py recognizes into that layout;
  picks `<Client>` from the source and the start from the first timestamp
  (or `--start` for undated exports). Tests: `test_saving.py`.
- `save_claude_code_session.py` — local Claude Code sessions: finds a
  workspace folder's sessions under
  `~/.claude/projects/`, lists them, and saves one through saving.py. It
  matches sessions by the `cwd` they recorded, because the projects
  directory name replaces every non-`[A-Za-z0-9]` character of the path
  with `-`, so different folders with non-Latin names share a directory.
  Tests: `test_save_claude_code_session.py`.
- `save_codex_session.py` — local Codex / ChatGPT Code/Work discovery and
  snapshot saving; title indexes are read-only, transcripts come from JSONL.
  Tests: `test_codex_session.py` and `fixtures/codex_jsonl/`.
- `sources/` — one file per source, each exposing `detect(path)` and
  `load_atoms(path)`: `claude_jsonl.py` (Claude Code sessions), `codex_jsonl.py` (local
  Codex / ChatGPT Code/Work rollouts),
  `claude_export.py` (claude.ai exports), `chatgpt_export.py` (chatgpt.com
  exports), `gemini_export.py` (gemini.google.com exports),
  `google_export.py` (Google AI
  Mode exports made by the extension), `google_saved_page.py` (a Google AI
  Mode page saved from Chrome, or its slim copy), `deepseek_export.py`
  (DeepSeek share-page exports). A new source is a new file here plus one
  line in `convert.py`'s `SOURCES` list — `turns.py` doesn't change.
  The claude.ai, ChatGPT and Gemini exports come from one family of Chrome
  exporters and share a skeleton — marker-split sections, a date line
  first, a signature at the end, gaps from messages the page had not
  loaded — which lives once in `sources/exporter_family.py`; each of the
  three modules is only its dialect: markers, date format, signature, and
  how that provider's reasoning is cut out. Another exporter of the same
  shape is a new dialect module, not a copy of the skeleton.
- `slim_google_page.py` — cuts a saved Google AI Mode page (~18 MB, most of
  it stylesheets, scripts and the side panel with the viewer's whole search
  history) down to the turns alone (~0.7 MB) and writes that copy into the
  chat's folder; the copy converts exactly like the full page, so it is the
  one that is kept. Tests:
  `tests/session_history_converter/test_google_saved_page.py`.

Deeper reference material for this tool lives alongside this file, in
[session_history_converter/](session_history_converter/). Read only the one
that actually applies to what you're doing:

- **Someone asks how to export a browser/cloud chat** from Claude, ChatGPT, Gemini,
  Google AI Mode, or DeepSeek — even outside any work on this tool, just a
  person wanting to save a conversation without a local rollout — read
  [session_history_converter/chrome-exporters.md](session_history_converter/chrome-exporters.md)
  and answer with the actual Chrome extension for that provider, by name
  and store link. This is the primary reason that file exists. It also maps
  each exporter's output signature to the `sources/*.py` module (if any)
  that already parses it, and to a real example in `sample_chats/` when one
  exists — useful when handed a file and asked what produced it, or when
  deciding whether a new source needs a parser at all before one is written.
- **Handed a Google AI Mode page saved from Chrome** (`<Title> - Google
  Search.html`, a `_files` folder beside it) — read
  [session_history_converter/google-ai-mode.md](session_history_converter/google-ai-mode.md):
  the slim step, how to confirm the dates, what to leave to the person.
- **Asked to support a new source** (any export that
  doesn't match `detect()` in any current `sources/*.py` module) — read
  [session_history_converter/known-sources.md](session_history_converter/known-sources.md)
  first: it says how to tell whether the export is one more dialect of the
  exporter family (a small module, not a new parser) and what to check in
  a real file before writing anything else.
- **A converted turn file has math that won't render** (a `tikzcd` diagram
  showing as raw text, a KaTeX parse error, `$...$` glued to surrounding
  prose) — read
  [session_history_converter/latex-math.md](session_history_converter/latex-math.md).
  This is a manual fix-up guide, not something `convert.py` does automatically.
