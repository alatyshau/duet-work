# Writing a tool for this skill

Read this when adding a script to `scripts/` or changing how one is built. Using a tool needs none of it.

## One tool, one folder

Every tool keeps its files in its own folder under `scripts/` — an entry script plus whatever modules it needs — so tools stay untangled once there are many and some have nothing to do with each other. A tool made of several files (a shared module plus one file per source or variant, the way `session_history_converter` is built) beats one ever-growing script: at ten or twenty variants a monolith stops being maintainable.

## Running: `uv run --script`

Every entry script runs via `uv run --script scripts/<tool>/<entry>.py`. Packages it needs are declared in the script's own header per PEP 723, with exact versions:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
```

`uv` builds the environment outside the working folder. That matters because these scripts run from context folders on the synced drive: a `venv`, `node_modules` or cache directory created next to them would sync to every machine through the cloud.

No `uv` on the machine — don't work around it; tell the user the install command and stop:

```bash
which uv || echo "uv not found"
```

| OS | Install command |
|---|---|
| macOS | `brew install uv` |
| Debian/Ubuntu | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Windows | `winget install --id=astral-sh.uv -e` |

## No bytecode beside sibling modules

A multi-file tool sets a flag in its entry point **before** importing its sibling modules — otherwise Python writes a `__pycache__` next to them on every run, the same kind of junk on the synced drive:

```python
import sys
sys.dont_write_bytecode = True      # strictly before importing a sibling
sys.path.insert(0, str(Path(__file__).parent))
from turns import render_turn       # safe now
```

The entry point itself never caches its own bytecode (Python doesn't write it for a file run as a script) — the flag exists for what it imports.

## Tests

Tests live in `tests/<tool>/` and run with `uv run --with pytest pytest` from the repository root, which is also what CI runs. `tests/<tool>/conftest.py` makes the tool's modules importable as plain top-level names, the way the entry script imports them. Prefer fixture cases (an input file next to its `expected/` output) over assertions in code where the tool transforms files: a case can be read side by side without reading any Python.
