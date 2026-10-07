#!/usr/bin/env python3
"""Checks for the backlog plugin that need no judgement.

    backlog_check.py spec <issue>     the specification is complete and consistent
    backlog_check.py tests <issue>    every scenario has a test, and no other test was touched
    backlog_check.py closed           nothing belonging to a closed issue has been edited

Run from the project root. Reads .claude/refine.json. Standard library only.
Exit status: 0 all checks passed, 1 at least one failed, 2 the check could not run.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CHANGES_SECTION = "Changes to earlier specifications"
STATUSES = ("Draft", "Ready")

# A scenario ID is the specification's number and a sequence: 0042-03.
BARE_ID = re.compile(r"(?<![\w@-])(\d{4}-\d{2})(?![\w-])")
TAG = re.compile(r"@(\d{4}-\d{2})(?![\w-])")
SCENARIO = re.compile(r"^\s*Scenario( Outline| Template)?:\s*(.*)$")
REQUIREMENT = re.compile(r"^\s*-\s+\**(FR-\d+)\**\s*:")
LINK = re.compile(r"\]\(([^)#\s]+)(#[^)]*)?\)")
TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|specs?)/"
    r"|(^|/)test_[^/]*$"
    r"|[._-](test|spec)\.[^/.]+$"
    r"|_test\.[^/.]+$"
)


class CannotRun(Exception):
    pass


class Report:
    def __init__(self):
        self.failures = []
        self.warnings = []
        self.passed = 0

    def check(self, ok, message):
        if ok:
            self.passed += 1
        else:
            self.failures.append(message)

    def warn(self, message):
        self.warnings.append(message)

    def finish(self):
        for message in self.failures:
            print(f"FAIL  {message}")
        for message in self.warnings:
            print(f"WARN  {message}")
        print(
            f"{self.passed} passed, {len(self.failures)} failed, "
            f"{len(self.warnings)} warnings"
        )
        return 1 if self.failures else 0


def git(*args):
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise CannotRun(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def load_config():
    path = Path(".claude/refine.json")
    if not path.is_file():
        raise CannotRun("no .claude/refine.json; run the refine command first")
    config = json.loads(path.read_text())
    paths = config.get("paths", {})
    return {
        "repo": config.get("repo"),
        "featuresDir": paths.get("featuresDir", "docs/specs").rstrip("/"),
        "adrDir": paths.get("adrDir", "docs/decisions").rstrip("/"),
        "testPaths": config.get("implement", {}).get("testPaths"),
    }


def find_spec(config, issue):
    matches = sorted(Path(config["featuresDir"]).glob(f"{issue:04d}-*.md"))
    if not matches:
        raise CannotRun(
            f"no specification for issue {issue} in {config['featuresDir']}"
        )
    return matches[0]


class Spec:
    def __init__(self, path):
        self.path = Path(path)
        self.text = self.path.read_text()
        self.number = self.path.name[:4]
        self.sections = self._sections()
        self.scenarios = self._scenarios()  # (id or None, title)

    def _sections(self):
        sections, title, in_fence = {}, None, False
        for line in self.text.splitlines():
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
            if not in_fence and line.startswith("## "):
                title = line[3:].strip()
                sections[title] = []
            elif title is not None:
                sections[title].append(line)
        return {name: "\n".join(lines) for name, lines in sections.items()}

    def section(self, name):
        return self.sections.get(name, "")

    def gherkin_lines(self):
        in_block = False
        for line in self.text.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_block = stripped.startswith("```gherkin") and not in_block
                continue
            if in_block:
                yield line

    def _scenarios(self):
        scenarios, pending = [], []
        for line in self.gherkin_lines():
            stripped = line.strip()
            match = SCENARIO.match(line)
            if match:
                ids = [i for tag_line in pending for i in TAG.findall(tag_line)]
                scenarios.append((ids[0] if ids else None, match.group(2).strip()))
                pending = []
            elif stripped.startswith("@"):
                pending.append(stripped)
            elif stripped and not stripped.startswith("#"):
                pending = []
        return scenarios

    @property
    def ids(self):
        return [scenario_id for scenario_id, _ in self.scenarios if scenario_id]

    @property
    def status(self):
        match = re.search(r"^- \*\*Status:\*\*\s*(\S+)", self.text, re.MULTILINE)
        return match.group(1) if match else None

    def requirements(self):
        found = []
        for line in self.section("Requirements").splitlines():
            match = REQUIREMENT.match(line)
            if match:
                found.append(match.group(1))
        return found

    def ids_named_in(self, section):
        text = self.section(section)
        return set(BARE_ID.findall(text)) | set(TAG.findall(text))


def check_spec(config, issue, report):
    spec = Spec(find_spec(config, issue))
    name = spec.path.name

    report.check(
        spec.status in STATUSES,
        f"{name}: status is {spec.status!r}, expected one of {', '.join(STATUSES)}",
    )
    report.check(spec.scenarios, f"{name}: no scenarios found in a gherkin block")

    seen = set()
    for scenario_id, title in spec.scenarios:
        report.check(scenario_id, f"{name}: scenario has no ID: {title}")
        if not scenario_id:
            continue
        report.check(
            scenario_id.startswith(spec.number + "-"),
            f"{name}: @{scenario_id} does not start with this "
            f"specification's number {spec.number}: {title}",
        )
        report.check(
            scenario_id not in seen, f"{name}: @{scenario_id} is used more than once"
        )
        seen.add(scenario_id)

    gherkin = "\n".join(spec.gherkin_lines())
    strategy = spec.section("Testing strategy")
    requirements = spec.requirements()
    report.check(requirements, f"{name}: no functional requirements (FR-n) found")
    for requirement in requirements:
        cited = re.search(rf"\b{requirement}\b", gherkin + "\n" + strategy)
        report.check(
            cited,
            f"{name}: {requirement} is not cited by any scenario "
            "or by the testing strategy",
        )

    strategy_ids = spec.ids_named_in("Testing strategy")
    for scenario_id in spec.ids:
        report.check(
            scenario_id in strategy_ids,
            f"{name}: @{scenario_id} has no entry in the testing strategy",
        )

    report.check(
        CHANGES_SECTION in spec.sections,
        f"{name}: no section '{CHANGES_SECTION}'",
    )

    if spec.status == "Ready":
        open_items = spec.section("Open items").strip()
        report.check(
            open_items in ("None.", "None"),
            f"{name}: status is Ready but Open items is not 'None.'",
        )

    for target, _ in LINK.findall(spec.text):
        if re.match(r"[a-z][a-z0-9+.-]*:", target):
            continue
        report.check(
            (spec.path.parent / target).exists(),
            f"{name}: link does not resolve: {target}",
        )
    return spec


def project_files(config):
    docs = (config["featuresDir"] + "/", config["adrDir"] + "/")
    listed = git("ls-files", "-co", "--exclude-standard").splitlines()
    return [path for path in listed if not path.startswith(docs)]


def is_test_path(config, path):
    patterns = config["testPaths"]
    if patterns:
        return any(Path(path).match(pattern) for pattern in patterns)
    return bool(TEST_PATH.search(path))


def read(path):
    try:
        return Path(path).read_text()
    except (OSError, UnicodeDecodeError):
        return ""


def all_spec_ids(config):
    ids = set()
    for path in Path(config["featuresDir"]).glob("[0-9][0-9][0-9][0-9]-*.md"):
        ids.update(Spec(path).ids)
    return ids


def check_tests(config, issue, base, report):
    spec = Spec(find_spec(config, issue))
    name = spec.path.name
    if not spec.ids:
        raise CannotRun(f"{name} has no scenario IDs; run 'spec {issue}' first")

    files = project_files(config)
    tagged = {}  # id -> files that carry it
    for path in files:
        for scenario_id in set(TAG.findall(read(path))):
            tagged.setdefault(scenario_id, []).append(path)

    for scenario_id in spec.ids:
        report.check(
            scenario_id in tagged, f"@{scenario_id} is not carried by any test"
        )

    known = all_spec_ids(config)
    for scenario_id, paths in sorted(tagged.items()):
        report.check(
            scenario_id in known,
            f"@{scenario_id} in {paths[0]} is not a scenario in any specification",
        )

    # Existing tests may be changed or removed only where the specification says so.
    allowed = set(spec.ids) | spec.ids_named_in(CHANGES_SECTION)
    docs = (config["featuresDir"] + "/", config["adrDir"] + "/")
    for entry in git("diff", "--name-status", "--no-renames", base).splitlines():
        status, path = entry.split("\t", 1)
        if status == "A" or path.startswith(docs):
            continue
        before = git("show", f"{base}:{path}").splitlines()
        if not (is_test_path(config, path) or TAG.search("\n".join(before))):
            continue
        after = [] if status == "D" else read(path).splitlines()
        old_untagged, old_tests = split_tests(before)
        _, new_tests = split_tests(after)

        for position, (ids, old_body) in enumerate(old_tests):
            new_body = next(
                (body for new_ids, body in new_tests if new_ids == ids), None
            )
            is_last = position == len(old_tests) - 1
            if new_body == old_body or (
                is_last and moved_tail(old_body, new_body, after)
            ):
                continue
            what = "removed" if new_body is None else "changed"
            for scenario_id in ids:
                report.check(
                    scenario_id in allowed,
                    f"{path}: the test for @{scenario_id} was {what}, but {name} "
                    f"does not list it under '{CHANGES_SECTION}'",
                )

        # Code with no scenario ID cannot be tied to a specification, so a change
        # to it is reported for a person to look at.
        remaining = [line.strip() for line in after]
        for line in old_untagged:
            if line in remaining:
                remaining.remove(line)
            else:
                report.warn(
                    f"{path}: existing test code with no scenario ID was changed "
                    f"or removed; check it by hand: {line}"
                )


def split_tests(lines):
    """Split a file into its untagged lines and the text that follows each tag."""
    untagged, tests = [], []
    for line in lines:
        ids = tuple(TAG.findall(line))
        if ids:
            tests.append((ids, []))
        elif tests:
            tests[-1][1].append(line.rstrip())
        elif line.strip():
            untagged.append(line.strip())
    for _, body in tests:
        while body and not body[-1]:
            body.pop()
    return untagged, tests


def moved_tail(old_body, new_body, new_lines):
    """True when the last test only lost trailing lines that still end the file.

    New tests added after the last existing one take over whatever followed it,
    such as a main guard at the bottom of the file.
    """
    if new_body is None or old_body[: len(new_body)] != new_body:
        return False
    tail = [line.strip() for line in old_body[len(new_body) :] if line.strip()]
    end = [line.strip() for line in new_lines if line.strip()][-len(tail) :]
    return bool(tail) and tail == end


def check_closed(config, report):
    if not config["repo"]:
        raise CannotRun("no repo in .claude/refine.json")
    result = subprocess.run(
        [
            "gh", "issue", "list", "--repo", config["repo"], "--state", "closed",
            "--limit", "1000", "--json", "number,closedAt",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise CannotRun(f"gh issue list: {result.stderr.strip()}")

    features = Path(config["featuresDir"])
    adr_dir = Path(config["adrDir"]).resolve()
    frozen = {}  # file -> (closedAt, issue), earliest close wins
    for issue in json.loads(result.stdout):
        for spec_path in features.glob(f"{issue['number']:04d}-*.md"):
            paths = [spec_path]
            for target, _ in LINK.findall(spec_path.read_text()):
                linked = (spec_path.parent / target).resolve()
                if linked.is_file() and adr_dir in linked.parents:
                    paths.append(linked.relative_to(Path.cwd().resolve()))
            for path in paths:
                key = str(path)
                if key not in frozen or issue["closedAt"] < frozen[key][0]:
                    frozen[key] = (issue["closedAt"], issue["number"])

    for path, (closed_at, number) in sorted(frozen.items()):
        later = git(
            "log", "--format=%h %cI %s", f"--since={closed_at}", "--", path
        ).splitlines()
        report.check(
            not later,
            f"{path}: belongs to closed issue #{number} but was changed "
            f"afterwards in {later[0] if later else ''}",
        )
        dirty = git("status", "--porcelain", "--", path).strip()
        report.check(
            not dirty,
            f"{path}: belongs to closed issue #{number} "
            "and has uncommitted changes",
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    spec_parser = commands.add_parser("spec")
    spec_parser.add_argument("issue", type=int)
    tests_parser = commands.add_parser("tests")
    tests_parser.add_argument("issue", type=int)
    tests_parser.add_argument(
        "--base", default="HEAD", help="commit the work started from"
    )
    commands.add_parser("closed")
    args = parser.parse_args()

    report = Report()
    try:
        config = load_config()
        if args.command == "spec":
            check_spec(config, args.issue, report)
        elif args.command == "tests":
            check_tests(config, args.issue, args.base, report)
        else:
            check_closed(config, report)
    except CannotRun as error:
        print(f"CANNOT RUN  {error}")
        return 2
    return report.finish()


if __name__ == "__main__":
    sys.exit(main())
