---
name: duet-tools
description: Index of Duet tool scripts.
disable-model-invocation: true
---

# Duet Tools

An index of Duet tools. One tool, one folder under `scripts/` with its own entry script; the list below says what exists and when to use each one.

## Rule for every script here

Every script runs via `uv run --script scripts/<tool>/<entry>.py`. If it needs packages, they're declared in the script's own header per PEP 723 (`# /// script` ... `# ///`) with exact versions; `uv` builds the environment outside the working folder. Scripts in this skill run from context folders on the synced drive — no `venv`, `node_modules`, or cache directory is ever created next to them, since that kind of junk would sync to every machine through the cloud.

No `uv` on the machine — don't work around it, tell the user the install command and stop:

```bash
which uv || echo "uv not found"
```

| OS | Install command |
|---|---|
| macOS | `brew install uv` |
| Debian/Ubuntu | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Windows | `winget install --id=astral-sh.uv -e` |

**A tool made of several files** (a shared module plus one file per source/variant — that's how `session_history_converter` is built, rather than one ever-growing script) sets a flag in its entry point **before** importing its sibling modules — otherwise Python writes a `__pycache__` next to them on every run, which is the same kind of junk on the synced drive:

```python
import sys
sys.dont_write_bytecode = True      # strictly before importing a sibling
sys.path.insert(0, str(Path(__file__).parent))
from turns import render_turn       # safe now
```

The entry point itself never caches its own bytecode (Python doesn't write it for a file run as a script) — the flag exists for what it imports.

## Tools

### Session History Converter

Splits an AI conversation into one markdown file per turn, in our own
format — Claude Code sessions, claude.ai exports, Google AI Mode exports,
DeepSeek exports. See [references/session_history_converter.md](references/session_history_converter.md) for how it's organized and how to add a source.

```bash
uv run --script scripts/session_history_converter/convert.py <path-to-source>
```
