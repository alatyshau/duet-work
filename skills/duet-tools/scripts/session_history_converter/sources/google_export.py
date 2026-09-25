"""Source: Google AI Mode Exporter (google.com AI Mode), markdown.

The heading '### AI Mode reply for <prompt>' carries the prompt in its own
tail; there are no dates. The response is cut off at the share-panel button
block, and base64 image junk embedded in the text is dropped.

Produced by the "AI Chat Exporter" Chrome extension — see the skill's
references/session_history_converter/chrome-exporters.md for the browser
extensions this tool's sources are known to correspond to.
"""

import re
import sys
from pathlib import Path

from turns import Atom

REPLY_PREFIX = "### AI Mode reply for "
JUNK_MARKER = "Copied to clipboardFailed to copy to clipboard. Try again later."
IMAGE_JUNK = re.compile(r"!\[\]\(data:image/|sn\.\\?_setImageSrc\(")


def detect(path: Path) -> bool:
    if path.suffix != ".md":
        return False
    lines = path.read_text(encoding="utf-8").split("\n")
    return any(line.startswith(REPLY_PREFIX) for line in lines)


def _strip_image_junk(lines: list[str]) -> list[str]:
    """Cuts a line at the point the image junk starts, wherever that is;
    real text before it (if any) is kept."""
    out = []
    for line in lines:
        m = IMAGE_JUNK.search(line)
        if not m:
            out.append(line)
            continue
        prefix = line[: m.start()].rstrip()
        if any(ch.isalnum() for ch in prefix):
            out.append(prefix)
    return out


def load_atoms(path: Path) -> list[Atom]:
    lines = path.read_text(encoding="utf-8").split("\n")
    starts = [i for i, line in enumerate(lines) if line.startswith(REPLY_PREFIX)]
    atoms: list[Atom] = []
    for idx, i in enumerate(starts):
        prompt = lines[i][len(REPLY_PREFIX):]
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        marker = next((j for j in range(i + 1, end) if lines[j] == JUNK_MARKER), None)
        if marker is None:
            sys.exit(f"could not find the end-of-response marker after line {i + 1}")
        a_body = _strip_image_junk(lines[i + 1 : marker])  # heading normalization happens in turns.render_section
        atoms.append(Atom("prompt", text=prompt))
        atoms.append(Atom("response", text="\n".join(a_body).strip("\n")))
    return atoms
