#!/usr/bin/env python3
"""Check that the standards and the skills of this plugin refer to each other.

A skill or a connector is only worth shipping if a standard sends the reader
to it, and a standard must not send the reader to one that is not here. Run from the
plugin root. Exit 0 if every reference holds, 1 if not.
"""
import json
import re
import sys
from pathlib import Path

LOAD = re.compile(r"load the `dotnet-standards:([^`]+)` skill")
LOOKUP = re.compile(r"the `([^`]+)` connector of the dotnet-standards plugin")
RULE = re.compile(r"^\|\s*(S-[A-Z][A-Z0-9]*-\d+)\s*\|", re.MULTILINE)


def skills(root):
    """Skill name to the file that defines it.

    Claude Code offers a plugin's skill under its folder's name, so that is
    the name a standard has to use, whatever the skill's own header says.
    """
    return {
        path.parent.name: path for path in sorted(root.glob("skills/*/SKILL.md"))
    }


def connectors(root):
    """The names of the connectors this plugin supplies."""
    path = root / ".mcp.json"
    if not path.is_file():
        return set()
    return set(json.loads(path.read_text()).get("mcpServers", {}))


def check(root):
    failures = []
    present = skills(root)
    supplied = connectors(root)
    referenced = {}
    looked_up = set()
    rules = {}
    for path in sorted(root.glob("standards/*.md")):
        text = path.read_text()
        names = LOAD.findall(text)
        if not names:
            failures.append(f"{path.relative_to(root)} names no skill")
        for name in names:
            referenced.setdefault(name, path)
            if name not in present:
                failures.append(
                    f"{path.relative_to(root)} sends the reader to the skill "
                    f"'{name}', which is not in this plugin"
                )
        for name in LOOKUP.findall(text):
            looked_up.add(name)
            if name not in supplied:
                failures.append(
                    f"{path.relative_to(root)} sends the reader to the connector "
                    f"'{name}', which is not in this plugin"
                )
        for rule in RULE.findall(text):
            if rule in rules:
                failures.append(
                    f"{rule} is in both {rules[rule].relative_to(root)} "
                    f"and {path.relative_to(root)}"
                )
            rules[rule] = path
    for name, path in present.items():
        if name not in referenced:
            failures.append(
                f"{path.relative_to(root)} defines the skill '{name}', "
                f"which no standard refers to"
            )
    for name in sorted(supplied - looked_up):
        failures.append(
            f".mcp.json supplies the connector '{name}', "
            f"which no standard refers to"
        )
    return failures


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    failures = check(root)
    for line in failures:
        print(f"FAIL  {line}")
    print(f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
