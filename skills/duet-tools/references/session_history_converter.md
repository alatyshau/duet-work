# Session History Converter

`scripts/session_history_converter/convert.py` splits an AI conversation
into files by turn (our own format — see the script's own docstring for the
exact shape): `NN_MMDD_HHMM.md` next to the source, one file per human turn.

```bash
uv run --script scripts/session_history_converter/convert.py <path-to-source>
```

## Layout

The output format is a growing part of the tool itself, not of any one
source, so the tool has its own folder rather than living loose in
`scripts/`:

- `turns.py` — the shared model and renderer. Every source reduces its
  input to this shape; the format itself lives only here.
- `sources/` — one file per source, each exposing `detect(path)` and
  `load_atoms(path)`: `claude_jsonl.py` (Claude Code sessions),
  `claude_export.py` (claude.ai exports), `google_export.py` (Google AI
  Mode exports), `deepseek_export.py` (DeepSeek share-page exports). A new
  source is a new file here plus one line in `convert.py`'s `SOURCES`
  list — `turns.py` doesn't change.

Deeper reference material for this tool lives alongside this file, in
[session_history_converter/](session_history_converter/). Read only the one
that actually applies to what you're doing:

- **Someone asks how to export a chat** from Claude, ChatGPT, Gemini,
  Google AI Mode, or DeepSeek — even outside any work on this tool, just a
  person wanting to save a conversation — read
  [session_history_converter/chrome-exporters.md](session_history_converter/chrome-exporters.md)
  and answer with the actual Chrome extension for that provider, by name
  and store link. This is the primary reason that file exists. It also maps
  each exporter's output signature to the `sources/*.py` module (if any)
  that already parses it, and to a real example in `sample_chats/` when one
  exists — useful when handed a file and asked what produced it, or when
  deciding whether a new source needs a parser at all before one is written.
- **Asked to support a new source** (Gemini, ChatGPT, or any export that
  doesn't match `detect()` in any current `sources/*.py` module) — read
  [session_history_converter/known-sources.md](session_history_converter/known-sources.md)
  first. It has the marker patterns already gathered for the common ones,
  so you don't start from a blank grep.
- **A converted turn file has math that won't render** (a `tikzcd` diagram
  showing as raw text, a KaTeX parse error, `$...$` glued to surrounding
  prose) — read
  [session_history_converter/latex-math.md](session_history_converter/latex-math.md).
  This is a manual fix-up guide, not something `convert.py` does automatically.

Every tool in this skill keeps its files in its own folder under
`scripts/`, so they stay untangled once there are many tools and some of
them have nothing to do with conversations at all.
