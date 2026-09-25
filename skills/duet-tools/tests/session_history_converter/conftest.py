"""Makes the tool's modules importable as plain top-level modules
(`from turns import ...`, `from sources import claude_jsonl`), the same way
convert.py itself imports them, without needing the tool to be an
installable package. Also pins the local timezone to UTC: claude_jsonl
converts each record's timestamp to the machine's local time, so a fixture's
expected output would otherwise depend on which timezone it's run in.
"""

import os
import sys
import time
from pathlib import Path

os.environ["TZ"] = "UTC"
if hasattr(time, "tzset"):
    time.tzset()

CONVERTER_DIR = Path(__file__).resolve().parents[2] / "scripts" / "session_history_converter"
sys.path.insert(0, str(CONVERTER_DIR))
