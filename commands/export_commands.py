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

# Commands worth putting in the "Useful" section even though their response
# doesn't contain a link. Hand-maintained - add to this if new info commands
# get added to commands.json.
USEFUL_KEYS = {
    "id", "lastid", "kit", "mic", "controller", "camera", "pc", "decks",
    "monitors", "headphones", "schedule", "weather", "time", "add", "so",
    "raid",
}


def is_useful(key, response):
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
        (useful if is_useful(key, response) else other).append(record)

    key_fn = lambda r: r["trigger"].lower()
    useful.sort(key=key_fn)
    other.sort(key=key_fn)
    return {"useful": useful, "other": other}


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    if not source.exists():
        raise SystemExit(f"commands.json not found at {source}")

    data = json.loads(source.read_text(encoding="utf-8"))
    records = build_records(data.get("commands", {}))

    html = PAGE.read_text(encoding="utf-8")
    if START_MARKER not in html or END_MARKER not in html:
        raise SystemExit(f"Markers not found in {PAGE} - page template may have changed.")

    payload = "var COMMANDS = " + json.dumps(records, ensure_ascii=False, indent=2) + ";"
    replacement = f"{START_MARKER}\n  {payload}\n  {END_MARKER}"
    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    # Use a function repl, not a string one - re.sub treats backslashes (\n, \1, ...)
    # in a string repl as template escapes, which mangles the \n already escaped
    # inside JSON string values by json.dumps.
    new_html = pattern.sub(lambda _m: replacement, html, count=1)
    PAGE.write_text(new_html, encoding="utf-8")

    print(f"Wrote {len(records['useful'])} useful + {len(records['other'])} other commands to {PAGE}")


if __name__ == "__main__":
    main()
