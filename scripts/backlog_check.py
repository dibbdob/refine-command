#!/usr/bin/env python3
"""Checks for the backlog plugin that need no judgement.

    backlog_check.py spec <issue>     the specification is complete and consistent
    backlog_check.py tests <issue>    every scenario has a test, and no other test was touched
    backlog_check.py closed           nothing belonging to a closed issue has been edited
    backlog_check.py state            issues, specifications and the index agree
    backlog_check.py behaviour        the behaviour folder is what the specifications generate
    backlog_check.py behaviour --add <issue>   bring a built specification into it
    backlog_check.py standards        list the project's standards and what each applies to
    backlog_check.py verify           run the project's own checks on the files that changed
    backlog_check.py red <issue> -- <test command>     record the new tests failing
    backlog_check.py green <issue> -- <test command>   the suite passes, after a red

Run from the project root. Reads .claude/refine.json. Standard library only.
Exit status: 0 all checks passed, 1 at least one failed, 2 the check could not run.
"""

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

CHANGES_SECTION = "Changes to current behaviour"
OLD_CHANGES_SECTION = "Changes to earlier specifications"
GENERATED = "<!-- Generated from the specifications by the backlog plugin. Do not edit. -->"
INCLUDED = "Specifications included:"
AUTO_ACCEPTED = "Accepted under the auto-accept policy"
SETTLED = "Settled by convention"
STANDARD = re.compile(r"\bS-[A-Z][A-Z0-9]*-\d+\b")
APPLIES = re.compile(r"^Applies to:\s*(.+)$", re.MULTILINE)
STATUSES = ("Draft", "Ready")

# A scenario ID is the specification's number and a sequence: 0042-03.
BARE_ID = re.compile(r"(?<![\w@-])(\d{4}-\d{2})(?![\w-])")
TAG = re.compile(r"@(\d{4}-\d{2})(?![\w-])")
AREA = re.compile(r"@area:(\S+)")
AREA_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*(/[a-z0-9]+(-[a-z0-9]+)*)*$")
CONTINUES = ("Examples:", "Scenarios:", "|", '"""')
TAG_ONLY = re.compile(r"^\W*(@\d{4}-\d{2}\W*)+$")
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
        "featureIndex": paths.get("featureIndex", "docs/specs/README.md"),
        "behaviourDir": paths.get("behaviourDir", "docs/behaviour").rstrip("/"),
        "conventions": paths.get("conventions", "docs/specs/CONVENTIONS.md"),
        "standardsDir": paths.get("standardsDir", "docs/standards").rstrip("/"),
        "verify": config.get("implement", {}).get("verify", []),
        "autoAccept": bool(config.get("process", {}).get("autoAccept", False)),
        "readyLabel": config.get("finalise", {}).get("readyLabel", "ready"),
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
        """Each scenario with its ID, area and text; self.scenarios keeps (id, title)."""
        lines = list(self.gherkin_lines())
        self.blocks, pending, feature_area, i = [], [], None, 0
        while i < len(lines):
            stripped = lines[i].strip()
            match = SCENARIO.match(lines[i])
            if stripped.startswith("Feature:"):
                feature_area = (AREA.findall(" ".join(pending)) or [None])[-1]
                pending = []
            elif match:
                tags = " ".join(line for line in pending if line.startswith("@"))
                ids = TAG.findall(tags)
                body = [stripped]
                i += 1
                while i < len(lines):
                    following = lines[i].strip()
                    if not following:
                        ahead = next((l.strip() for l in lines[i:] if l.strip()), "")
                        if not ahead.startswith(CONTINUES):
                            break
                    elif SCENARIO.match(lines[i]) or following.startswith("@"):
                        break
                    else:
                        body.append(following)
                    i += 1
                self.blocks.append(
                    {
                        "id": ids[0] if ids else None,
                        "title": match.group(2).strip(),
                        "area": (AREA.findall(tags) or [feature_area])[-1],
                        "body": body,
                    }
                )
                pending = []
                continue
            elif stripped.startswith(("@", "#")):
                pending.append(stripped)
            elif stripped:
                pending = []
            i += 1
        return [(block["id"], block["title"]) for block in self.blocks]

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

    def automation(self):
        """Each scenario ID's entry in the testing strategy's Automated column."""
        column, entries = None, {}
        for line in self.section("Testing strategy").splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if column is None:
                lowered = [cell.lower() for cell in cells]
                if "automated" in lowered:
                    column = lowered.index("automated")
                continue
            if column < len(cells):
                for scenario_id in BARE_ID.findall(line) + TAG.findall(line):
                    entries[scenario_id] = cells[column].lower()
        return entries

    @property
    def manual_ids(self):
        return {i for i, entry in self.automation().items() if entry == "no"}

    @property
    def automated_ids(self):
        return [i for i in self.ids if i not in self.manual_ids]

    def ids_named_in(self, section):
        text = self.section(section)
        return set(BARE_ID.findall(text)) | set(TAG.findall(text))

    @property
    def changes(self):
        """The name this specification uses for its changes section, if it has one."""
        for name in (CHANGES_SECTION, OLD_CHANGES_SECTION):
            if name in self.sections:
                return name
        return None

    @property
    def retires(self):
        """IDs of scenarios from other specifications that this one replaces or removes."""
        if not self.changes:
            return set()
        return self.ids_named_in(self.changes) - set(self.ids)


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

    for scenario_id, entry in spec.automation().items():
        report.check(
            entry in ("yes", "no"),
            f"{name}: the testing strategy must say Yes or No under Automated "
            f"for @{scenario_id}, not {entry!r}",
        )

    report.check(spec.changes, f"{name}: no section '{CHANGES_SECTION}'")

    in_force = behaviour_ids(config)
    existing_areas = set(in_force.values())
    for block in spec.blocks:
        area = block["area"]
        report.check(
            area and AREA_NAME.match(area),
            f"{name}: scenario has no area, or one that is not lowercase words "
            f"joined by hyphens and slashes: {block['title']} ({area})",
        )
    new_areas = sorted(
        area
        for area in {b["area"] for b in spec.blocks if b["area"]} - existing_areas
        if AREA_NAME.match(area)
    )
    for area in new_areas:
        report.warn(f"{name}: creates a new area in the behaviour folder: {area}")

    assumptions = spec.section("Assumptions")
    agreed = set(
        re.findall(r"^\|\s*(C-\d+)\s*\|", read(config["conventions"]), re.MULTILINE)
    )
    for convention in sorted(set(re.findall(r"\bC-\d+\b", assumptions))):
        report.check(
            convention in agreed,
            f"{name}: cites {convention}, which is not in {config['conventions']}",
        )
    known_standards = {rule for topic in standards(config) for rule in topic["rules"]}
    for rule in sorted(set(STANDARD.findall(spec.text))):
        report.check(
            rule in known_standards,
            f"{name}: cites {rule}, which is not in {config['standardsDir']}",
        )
    if AUTO_ACCEPTED in assumptions:
        # Nobody reviewed this specification, so it must have left nothing to review.
        listed = [
            line.strip()
            for line in assumptions.splitlines()
            if line.lstrip().startswith("- ") and SETTLED not in line
        ]
        report.check(
            config["autoAccept"],
            f"{name}: marked as auto-accepted, but process.autoAccept is not on",
        )
        report.check(
            not listed,
            f"{name}: marked as auto-accepted, but lists {len(listed)} assumptions "
            "that nobody has reviewed",
        )
        report.check(
            not spec.retires,
            f"{name}: marked as auto-accepted, but changes behaviour in force",
        )
        report.check(
            not new_areas,
            f"{name}: marked as auto-accepted, but creates a new area",
        )
    built = spec.number in included_specs(config)
    for scenario_id in sorted(set() if built else spec.retires):
        report.check(
            scenario_id in in_force,
            f"{name}: lists @{scenario_id} as changed, "
            "but that scenario is not in force",
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


def document_dirs(config):
    """Folders of documents, where a scenario ID names a scenario, not a test."""
    return tuple(
        config[key] + "/" for key in ("featuresDir", "adrDir", "behaviourDir")
    )


def project_files(config):
    docs = document_dirs(config)
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


def tagged_files(config):
    """Each scenario ID carried outside the documents, and the files carrying it."""
    tagged = {}
    for path in project_files(config):
        for scenario_id in set(TAG.findall(read(path))):
            tagged.setdefault(scenario_id, []).append(path)
    return tagged


def spec_paths(config):
    return sorted(Path(config["featuresDir"]).glob("[0-9][0-9][0-9][0-9]-*.md"))


def all_spec_ids(config):
    ids = set()
    for path in spec_paths(config):
        ids.update(Spec(path).ids)
    return ids


def check_tests(config, issue, base, report):
    spec = Spec(find_spec(config, issue))
    name = spec.path.name
    if not spec.ids:
        raise CannotRun(f"{name} has no scenario IDs; run 'spec {issue}' first")

    tagged = tagged_files(config)
    for scenario_id in spec.automated_ids:
        report.check(
            scenario_id in tagged, f"@{scenario_id} is not carried by any test"
        )
    for scenario_id in sorted(spec.manual_ids - set(tagged)):
        report.warn(
            f"@{scenario_id} is verified by hand, not by a test; "
            "carry out its procedure and record the result"
        )

    known = all_spec_ids(config)
    for scenario_id, paths in sorted(tagged.items()):
        report.check(
            scenario_id in known,
            f"@{scenario_id} in {paths[0]} is not a scenario in any specification",
        )

    # Existing tests may be changed or removed only where the specification says so.
    allowed = set(spec.ids) | spec.retires
    docs = document_dirs(config)
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

        for ids, old_body in old_tests:
            new_body = next(
                (body for new_ids, body in new_tests if new_ids == ids), None
            )
            if new_body == old_body:
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


def indent_of(line):
    expanded = line.expandtabs()
    return len(expanded) - len(expanded.lstrip())


def split_tests(lines):
    """Split a file into the test that follows each tag, and everything else.

    A test is the lines after its tag, down to where the indentation returns to
    the tag's own level or less once the test's body has begun. What follows
    it there, such as the header of the next class or a guard at the foot of
    the file, is not part of the test, so adding tests after it does not count
    as changing it.
    """
    other, tests, current = [], [], None
    for line in lines:
        ids = tuple(TAG.findall(line))
        if ids:
            current = {"indent": indent_of(line), "in_body": False, "done": False}
            tests.append((ids, []))
            continue
        if current and not current["done"]:
            if not line.strip():
                tests[-1][1].append("")
                continue
            if indent_of(line) > current["indent"]:
                current["in_body"] = True
            elif current["in_body"]:
                current["done"] = True
            if not current["done"]:
                tests[-1][1].append(line.rstrip())
                continue
        if line.strip():
            other.append(line.strip())
    for _, body in tests:
        while body and not body[-1]:
            body.pop()
    return other, tests


def check_closed(config, report):
    closed = gh_issues(config, "closed", "number,closedAt")

    features = Path(config["featuresDir"])
    adr_dir = Path(config["adrDir"]).resolve()
    frozen = {}  # file -> (closedAt, issue), earliest close wins
    for issue in closed:
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


def gh_issues(config, state, fields):
    if not config["repo"]:
        raise CannotRun("no repo in .claude/refine.json")
    result = subprocess.run(
        [
            "gh", "issue", "list", "--repo", config["repo"], "--state", state,
            "--limit", "1000", "--json", fields,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise CannotRun(f"gh issue list: {result.stderr.strip()}")
    return json.loads(result.stdout)


def check_state(config, report):
    """The issue, the specification and the feature index tell the same story."""
    issues = {
        issue["number"]: issue
        for issue in gh_issues(config, "all", "number,state,labels,body")
    }
    index = read(config["featureIndex"])
    tagged = tagged_files(config)
    specs = [Spec(path) for path in spec_paths(config)]
    retired = set()
    for spec in specs:
        retired |= spec.retires

    for spec in specs:
        name, number = spec.path.name, int(spec.number)
        issue = issues.get(number)
        report.check(issue, f"{name}: there is no issue #{number} in {config['repo']}")
        if not issue:
            continue

        if issue["state"] == "CLOSED":
            report.check(
                spec.status == "Ready",
                f"{name}: issue #{number} is closed but the specification is "
                f"{spec.status}",
            )
            if spec.ids:
                report.check(
                    spec.number in included_specs(config),
                    f"{name}: issue #{number} is closed but the specification "
                    f"is not in {config['behaviourDir']}",
                )
            for scenario_id in spec.automated_ids:
                report.check(
                    scenario_id in tagged or scenario_id in retired,
                    f"{name}: issue #{number} is closed but @{scenario_id} is "
                    "carried by no test and no later specification retires it",
                )
        elif config["readyLabel"]:
            labelled = config["readyLabel"] in {
                label["name"] for label in issue["labels"]
            }
            report.check(
                labelled == (spec.status == "Ready"),
                f"{name}: the specification is {spec.status} but issue #{number} "
                f"{'has' if labelled else 'does not have'} the "
                f"'{config['readyLabel']}' label",
            )

        body = issue["body"] or ""
        report.check(
            name in body, f"{name}: issue #{number} does not link to it"
        )
        stated = re.search(r"Status:\s*\*\*(\w+)\*\*", body)
        report.check(
            stated and stated.group(1) == spec.status,
            f"{name}: the specification is {spec.status} but issue #{number} "
            f"says {stated.group(1) if stated else 'nothing about its status'}",
        )

        rows = [line for line in index.splitlines() if name in line]
        report.check(rows, f"{name}: not listed in {config['featureIndex']}")
        if rows:
            report.check(
                spec.status in rows[0],
                f"{name}: the specification is {spec.status} but "
                f"{config['featureIndex']} shows something else",
            )


def included_specs(config):
    """Numbers of the specifications the behaviour folder was generated from."""
    for line in read(Path(config["behaviourDir"]) / "README.md").splitlines():
        if line.startswith(INCLUDED):
            return re.findall(r"\d{4}", line[len(INCLUDED) :])
    return []


def generate_behaviour(config, numbers):
    """The behaviour folder's files, as {path relative to it: text}."""
    specs = []
    for number in sorted(set(numbers)):
        specs.append(Spec(find_spec(config, int(number))))
    retired, area_of = set(), {}
    for spec in specs:
        retired |= spec.retires
        for block in spec.blocks:
            if block["id"]:
                if not block["area"]:
                    raise CannotRun(
                        f"{spec.path.name}: @{block['id']} has no area; "
                        f"run 'spec {int(spec.number)}' first"
                    )
                area_of[block["id"]] = block["area"]

    areas, last_changed = {}, {}
    for spec in specs:
        for block in spec.blocks:
            if block["id"] and block["id"] not in retired:
                areas.setdefault(block["area"], []).append(block)
            if block["id"]:
                last_changed[block["area"]] = spec.number
        for scenario_id in spec.retires:
            if scenario_id in area_of:
                last_changed[area_of[scenario_id]] = spec.number

    files = {}
    rows = []
    for area in sorted(areas):
        blocks = sorted(areas[area], key=lambda block: block["id"])
        lines = [
            f"# {area}",
            "",
            GENERATED,
            "",
            "What the system does today in this area. Each scenario carries the ID "
            "it was given by the specification that introduced it.",
            "",
            "```gherkin",
            f"Feature: {area}",
        ]
        for block in blocks:
            lines += ["", f"  @{block['id']}", f"  {block['body'][0]}"]
            for step in block["body"][1:]:
                indent = "      " if step.startswith("|") else "    "
                lines.append(indent + step)
        lines += ["```", ""]
        files[f"{area}.md"] = "\n".join(lines)
        rows.append(
            f"| [{area}]({area}.md) | {len(blocks)} | {last_changed[area]} |"
        )

    files["README.md"] = "\n".join(
        [
            "# Behaviour",
            "",
            GENERATED,
            "",
            "What the system does today, one file for each area. It is generated "
            "from the specifications that have been built: their scenarios, less "
            "any that a later specification replaced or removed. The "
            "specifications themselves hold the history and the reasons.",
            "",
            "| Area | Scenarios | Last changed by |",
            "|------|-----------|-----------------|",
            *rows,
            "",
            f"{INCLUDED} {', '.join(spec.number for spec in specs)}",
            "",
        ]
    )
    return files


def behaviour_ids(config):
    """Each scenario ID in force, with its area, read from the folder as it stands."""
    in_force = {}
    root = Path(config["behaviourDir"])
    if not root.is_dir():
        return in_force
    for path in root.rglob("*.md"):
        if path.name == "README.md" and path.parent == root:
            continue
        area = str(path.relative_to(root))[: -len(".md")]
        for scenario_id in TAG.findall(path.read_text()):
            in_force[scenario_id] = area
    return in_force


def check_behaviour(config, report):
    """The folder holds exactly what its specifications generate."""
    root = Path(config["behaviourDir"])
    expected = generate_behaviour(config, included_specs(config))
    on_disk = (
        {str(path.relative_to(root)) for path in root.rglob("*.md")}
        if root.is_dir()
        else set()
    )
    if not on_disk and len(expected) == 1:
        print(f"no behaviour folder yet at {root}")
        return
    for relative, text in sorted(expected.items()):
        report.check(
            read(root / relative) == text,
            f"{root / relative}: differs from what the specifications generate; "
            "it was edited by hand or is out of date",
        )
    for relative in sorted(on_disk - set(expected)):
        report.check(False, f"{root / relative}: not generated from any specification")


def add_to_behaviour(config, issue, report):
    """Regenerate the folder with one more specification in it."""
    spec = Spec(find_spec(config, issue))
    if not spec.ids:
        raise CannotRun(f"{spec.path.name} has no scenario IDs")
    root = Path(config["behaviourDir"])
    files = generate_behaviour(config, included_specs(config) + [spec.number])
    stale = (
        {str(path.relative_to(root)) for path in root.rglob("*.md")} - set(files)
        if root.is_dir()
        else set()
    )
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if read(path) != text:
            path.write_text(text)
            print(f"wrote {path}")
    for relative in sorted(stale):
        (root / relative).unlink()
        print(f"removed {root / relative}")
    report.check(True, "")


def standards(config):
    """Each topic in the standards folder: its file, what it applies to, its rules."""
    root = Path(config["standardsDir"])
    topics = []
    if not root.is_dir():
        return topics
    for path in sorted(root.rglob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text()
        applies = APPLIES.search(text)
        topics.append(
            {
                "path": str(path),
                "applies": applies.group(1).strip() if applies else None,
                "rules": re.findall(
                    r"^\|\s*(S-[A-Z][A-Z0-9]*-\d+)\s*\|", text, re.MULTILINE
                ),
            }
        )
    return topics


def globs_in(text):
    """The path patterns written in backticks in an 'Applies to' line."""
    return re.findall(r"`([^`]+)`", text or "")


def glob_regex(pattern):
    """A path pattern as a regular expression: ** crosses folders, * does not."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def matches(path, patterns):
    return any(glob_regex(pattern).match(path) for pattern in patterns)


def changed_files(base):
    tracked = git("diff", "--name-only", "--no-renames", base).splitlines()
    untracked = git("ls-files", "-o", "--exclude-standard").splitlines()
    return sorted(set(tracked + untracked))


def check_standards(config, report):
    """List the standards, and check each topic is usable."""
    topics = standards(config)
    if not topics:
        print(f"no standards yet in {config['standardsDir']}")
        return
    seen = {}
    for topic in topics:
        print(f"{topic['path']}  applies to: {topic['applies']}  rules: {len(topic['rules'])}")
        report.check(
            topic["applies"],
            f"{topic['path']}: no 'Applies to:' line saying what it covers",
        )
        for rule in topic["rules"]:
            report.check(
                rule not in seen,
                f"{topic['path']}: {rule} is also in {seen.get(rule)}",
            )
            seen[rule] = topic["path"]


def run_verify(config, base, report):
    """Run the project's own checks that apply to the files changed since base."""
    entries = config["verify"]
    if not entries:
        print("no checks configured under implement.verify")
        return
    files = changed_files(base)
    for entry in entries:
        command = entry if isinstance(entry, str) else entry.get("run")
        when = [] if isinstance(entry, str) else entry.get("when", [])
        if not command:
            raise CannotRun(f"implement.verify entry has no command: {entry!r}")
        if when and not any(matches(path, when) for path in files):
            print(f"skipped (no changed file matches {', '.join(when)}): {command}")
            continue
        print(f"running: {command}", flush=True)
        status = subprocess.run(command, shell=True).returncode
        report.check(status == 0, f"'{command}' failed with exit status {status}")

    # Say which standards cover the changed files, so none is overlooked.
    for topic in standards(config):
        patterns = globs_in(topic["applies"])
        touched = [path for path in files if matches(path, patterns)]
        if touched:
            print(
                f"standards that apply to {len(touched)} changed file(s): "
                f"{topic['path']}"
            )


def evidence_file(issue):
    return Path(git("rev-parse", "--git-dir").strip()) / "backlog" / f"{issue:04d}.json"


def test_digests(config, spec):
    """A fingerprint of the test that follows each of this specification's IDs."""
    wanted, digests = set(spec.automated_ids), {}
    for paths in tagged_files(config).values():
        for path in paths:
            _, tests = split_tests(read(path).splitlines())
            for ids, body in tests:
                for scenario_id in wanted.intersection(ids):
                    text = "\n".join(body).encode()
                    digests[scenario_id] = hashlib.sha256(text).hexdigest()
    return digests


def run_suite(command):
    if not command:
        raise CannotRun("give the test command after '--'")
    try:
        return subprocess.run(command).returncode
    except OSError as error:
        raise CannotRun(f"{' '.join(command)}: {error}")


def only_ids_added(config):
    """True when the working copy differs from HEAD only by scenario ID lines.

    That is a baseline: existing tests are being tied to scenarios and nothing
    else is changing, so there is no failing run to record.
    """
    docs = document_dirs(config)
    untracked = git("ls-files", "-o", "--exclude-standard").splitlines()
    if any(not path.startswith(docs) for path in untracked):
        return False
    added, in_docs = False, False
    for line in git("diff", "-U0", "--no-renames", "HEAD").splitlines():
        if line.startswith("diff --git "):
            in_docs = line.split(" b/", 1)[-1].startswith(docs)
        elif in_docs or line.startswith(("+++", "---")):
            continue
        elif line.startswith("-"):
            return False
        elif line.startswith("+") and line[1:].strip():
            if not TAG_ONLY.match(line[1:]):
                return False
            added = True
    return added


def record_red(config, issue, command, report):
    """The new tests exist and the suite fails, before the code is written."""
    spec = Spec(find_spec(config, issue))
    if not spec.automated_ids:
        print("no automated scenarios in this specification; nothing to record")
        return
    digests = test_digests(config, spec)
    for scenario_id in spec.automated_ids:
        report.check(
            scenario_id in digests,
            f"@{scenario_id} has no test yet; every test is written before the code",
        )
    status = run_suite(command)
    baseline = status == 0 and only_ids_added(config)
    if baseline:
        print(
            "baseline: the only change is scenario IDs on existing tests, "
            "so the suite is expected to pass"
        )
    else:
        report.check(
            status != 0,
            "the suite passed before the code was written, "
            "so the new tests do not show that anything was missing",
        )
    if report.failures:
        return
    path = evidence_file(issue)
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "head": git("rev-parse", "HEAD").strip(),
                "command": command,
                "exit": status,
                "baseline": baseline,
                "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "tests": digests,
            },
            indent=2,
        )
    )
    print(f"recorded: {len(digests)} tests, suite exit {status}")


def check_green(config, issue, command, report):
    """The suite passes, and the tests were seen to fail first."""
    spec = Spec(find_spec(config, issue))
    if not spec.automated_ids:
        print("no automated scenarios in this specification; nothing to run")
        return
    path = evidence_file(issue)
    report.check(
        path.is_file(),
        f"there is no record of the tests for issue {issue} failing before the "
        "code was written",
    )
    status = run_suite(command)
    report.check(status == 0, f"the suite failed with exit status {status}")
    if not path.is_file():
        return
    evidence = json.loads(path.read_text())
    head = git("rev-parse", "HEAD").strip()
    report.check(
        evidence["head"] == head,
        f"the failing run was recorded against commit {evidence['head'][:7]}, "
        f"not the current {head[:7]}",
    )
    digests = test_digests(config, spec)
    for scenario_id in spec.automated_ids:
        if digests.get(scenario_id) != evidence["tests"].get(scenario_id):
            report.warn(
                f"the test for @{scenario_id} was changed after it was seen to fail"
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
    commands.add_parser("state")
    commands.add_parser("standards")
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument(
        "--base", default="HEAD", help="commit the work started from"
    )
    behaviour_parser = commands.add_parser("behaviour")
    behaviour_parser.add_argument("--add", type=int, metavar="ISSUE")
    for name in ("red", "green"):
        run_parser = commands.add_parser(name)
        run_parser.add_argument("issue", type=int)
        run_parser.add_argument("test_command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command in ("red", "green") and args.test_command[:1] == ["--"]:
        args.test_command = args.test_command[1:]

    report = Report()
    try:
        config = load_config()
        if args.command == "spec":
            check_spec(config, args.issue, report)
        elif args.command == "tests":
            check_tests(config, args.issue, args.base, report)
        elif args.command == "closed":
            check_closed(config, report)
        elif args.command == "state":
            check_state(config, report)
        elif args.command == "standards":
            check_standards(config, report)
        elif args.command == "verify":
            run_verify(config, args.base, report)
        elif args.command == "behaviour" and args.add:
            add_to_behaviour(config, args.add, report)
        elif args.command == "behaviour":
            check_behaviour(config, report)
        elif args.command == "red":
            record_red(config, args.issue, args.test_command, report)
        else:
            check_green(config, args.issue, args.test_command, report)
    except CannotRun as error:
        print(f"CANNOT RUN  {error}")
        return 2
    return report.finish()


if __name__ == "__main__":
    sys.exit(main())
