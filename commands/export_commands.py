#!/usr/bin/env python3
"""Regenerates commands/index.html's embedded command list from
streaming-automation's commands.json.

Run this locally whenever commands.json changes:

    python export_commands.py [path/to/commands.json]

With no argument, defaults to ../../streaming-automation/commands.json,
matching the sibling-folder layout under K:\\Dev\\. Only commands with
enabled: true are included.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parent.parent / "streaming-automation" / "commands.json"
PAGE = HERE / "index.html"

START_MARKER = "/* COMMANDS:START */"
END_MARKER = "/* COMMANDS:END */"

# Fallback for commands with no explicit "public_useful" field set (older
# entries from before that field existed, or ones nobody's touched yet).
# Mark a command explicitly via the dashboard's Command Manager tab
# ("Mark useful" button) instead of editing this list where possible.
USEFUL_KEYS = {
    "id", "lastid", "kit", "mic", "controller", "camera", "pc", "decks",
    "monitors", "headphones", "schedule", "weather", "time", "add", "so",
    "raid",
}


def is_useful(key, cmd):
    if "public_useful" in cmd:
        return bool(cmd["public_useful"])
    response = cmd.get("response", "")
    return key in USEFUL_KEYS or "http://" in response or "https://" in response


def build_records(commands):
    useful, other = [], []
    for key, cmd in commands.items():
        if not cmd.get("enabled", False):
            continue
        response = cmd.get("response", "")
        record = {
            "trigger": key,
            "response": response,
            "kind": cmd.get("response_type", "static"),
        }
        access = cmd.get("access", "everyone")
        if access != "everyone":
            record["access"] = access
        (useful if is_useful(key, cmd) else other).append(record)

    key_fn = lambda r: r["trigger"].lower()
    useful.sort(key=key_fn)
    other.sort(key=key_fn)
    return {"useful": useful, "other": other}


def regenerate(source=None):
    """Rewrite index.html's embedded data from commands.json. Returns a dict
    of counts (useful, other, hidden = disabled commands not published) for
    callers that want a summary instead of parsing printed text."""
    source = Path(source) if source else DEFAULT_SOURCE
    if not source.exists():
        raise FileNotFoundError(f"commands.json not found at {source}")

    data = json.loads(source.read_text(encoding="utf-8"))
    commands = data.get("commands", {})
    records = build_records(commands)

    html = PAGE.read_text(encoding="utf-8")
    if START_MARKER not in html or END_MARKER not in html:
        raise RuntimeError(f"Markers not found in {PAGE} - page template may have changed.")

    payload = "var COMMANDS = " + json.dumps(records, ensure_ascii=False, indent=2) + ";"
    replacement = f"{START_MARKER}\n  {payload}\n  {END_MARKER}"
    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    # Use a function repl, not a string one - re.sub treats backslashes (\n, \1, ...)
    # in a string repl as template escapes, which mangles the \n already escaped
    # inside JSON string values by json.dumps.
    new_html = pattern.sub(lambda _m: replacement, html, count=1)
    PAGE.write_text(new_html, encoding="utf-8")

    useful, other = len(records["useful"]), len(records["other"])
    return {
        "useful": useful,
        "other": other,
        "hidden": len(commands) - (useful + other),
    }


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        counts = regenerate(source)
    except (FileNotFoundError, RuntimeError) as e:
        raise SystemExit(str(e))
    print(f"Wrote {counts['useful']} useful + {counts['other']} other commands to {PAGE} "
          f"({counts['hidden']} disabled, not published)")


if __name__ == "__main__":
    main()
