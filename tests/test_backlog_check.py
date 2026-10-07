"""Tests for scripts/backlog_check.py.

Each test builds a small project in a temporary git repository and runs the
checker against it as a separate process, the way the commands do. GitHub is
replaced by a stand-in `gh` that answers from a file.

    python3 -m unittest discover -s tests
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "backlog_check.py"

PASSING = [sys.executable, "-c", "import sys"]
FAILING = [sys.executable, "-c", "import sys; sys.exit(1)"]

FAKE_GH = """#!/usr/bin/env python3
import json, os, sys
issues = json.load(open(os.environ["FAKE_GH_ISSUES"]))
state = sys.argv[sys.argv.index("--state") + 1]
if state != "all":
    issues = [issue for issue in issues if issue["state"].lower() == state]
print(json.dumps(issues))
"""


def scenario(sequence, title=None, number=1, **options):
    """One scenario of a specification, as spec() expects it."""
    scenario_id = f"{number:04d}-{sequence:02d}"
    return {"id": scenario_id, "title": title or f"scenario {sequence}", **options}


def spec(number=1, scenarios=None, **options):
    """The text of a specification. Options override one part at a time."""
    scenarios = scenarios if scenarios is not None else [scenario(1, number=number)]
    requirements = options.get("requirements", ["FR-1"])
    gherkin, rows = [], []
    for item in scenarios:
        gherkin.append(f"  # {item.get('cites', 'FR-1')}")
        tags = item.get("tags", f"@{item['id']}" if item["id"] else "")
        if tags:
            gherkin.append(f"  {tags}")
        gherkin.append(f"  {item.get('keyword', 'Scenario')}: {item['title']}")
        gherkin += [f"    {step}" for step in item.get("steps", ["Then it works"])]
        gherkin.append("")
        if item.get("in_strategy", True) and item["id"]:
            rows.append(
                f"| {item['id']} {item['title']} | {item.get('automated', 'Yes')} | x |"
            )
    feature_tag = options.get("area", "core")
    lines = [
        f"# {number:04d}: Thing",
        "",
        f"- **Status:** {options.get('status', 'Ready')}",
        f"- **Issue:** #{number}",
        f"- **Decisions:** {options.get('decisions', 'none')}",
        "",
        "## Requirements",
        "",
        "### Functional",
        "",
        *[f"- {requirement}: does something" for requirement in requirements],
        "",
        "## Acceptance criteria",
        "",
        "```gherkin",
        *([f"@area:{feature_tag}"] if feature_tag else []),
        "Feature: thing",
        "",
        *gherkin,
        "```",
        "",
    ]
    changes_title = options.get("changes_title", "Changes to current behaviour")
    if changes_title:
        lines += [f"## {changes_title}", "", options.get("changes", "None."), ""]
    lines += [
        "## Design",
        "",
        options.get("design", "Nothing to say."),
        "",
        "## Testing strategy",
        "",
        options.get("strategy_note", ""),
        "",
        "| Scenario | Automated | How it is verified |",
        "|----------|-----------|--------------------|",
        *rows,
        "",
        "## Assumptions",
        "",
        options.get("assumptions", "- Something was assumed."),
        "",
        "## Open items",
        "",
        options.get("open_items", "None."),
        "",
    ]
    return "\n".join(lines)


def test_file(ids, untagged="", bodies=None, tail=""):
    """A test file with one test under each scenario ID."""
    bodies = bodies or {}
    parts = ["import unittest", "", untagged]
    for scenario_id in ids:
        name = scenario_id.replace("-", "_")
        parts += [
            f"# @{scenario_id}",
            f"def test_{name}():",
            f"    {bodies.get(scenario_id, 'assert True')}",
            "",
            "",
        ]
    return "\n".join(parts) + tail


class Project:
    """A throwaway project with a git repository and a refine.json."""

    def __init__(self, case, config=None):
        self.dir = Path(tempfile.mkdtemp(prefix="backlog-check-"))
        case.addCleanup(shutil.rmtree, self.dir, True)
        self.env = dict(
            os.environ,
            GIT_AUTHOR_NAME="Test",
            GIT_AUTHOR_EMAIL="test@example.com",
            GIT_COMMITTER_NAME="Test",
            GIT_COMMITTER_EMAIL="test@example.com",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_SYSTEM=os.devnull,
            PYTHONDONTWRITEBYTECODE="1",
        )
        self.git("init", "-q", "-b", "main")
        self.config(config or {})

    def config(self, config):
        self.write(".claude/refine.json", json.dumps({"repo": "owner/name", **config}))

    def write(self, path, text):
        target = self.dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def read(self, path):
        return (self.dir / path).read_text()

    def git(self, *args, date=None):
        env = dict(self.env)
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(
            ["git", *args], cwd=self.dir, env=env, check=True, capture_output=True
        )

    def commit(self, date=None):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", "commit", date=date)

    def issues(self, issues):
        """Stand in for GitHub: `gh issue list` will answer with these."""
        bin_dir = self.dir.parent / (self.dir.name + "-bin")
        bin_dir.mkdir(exist_ok=True)
        fake = bin_dir / "gh"
        fake.write_text(FAKE_GH)
        fake.chmod(0o755)
        data = bin_dir / "issues.json"
        data.write_text(json.dumps(issues))
        self.env["PATH"] = f"{bin_dir}{os.pathsep}{self.env['PATH']}"
        self.env["FAKE_GH_ISSUES"] = str(data)

    def check(self, *args):
        result = subprocess.run(
            [sys.executable, str(CHECKER), *map(str, args)],
            cwd=self.dir,
            env=self.env,
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout + result.stderr


class CheckerCase(unittest.TestCase):
    def setUp(self):
        self.project = Project(self)

    def assertPasses(self, *args, warnings=0):
        status, output = self.project.check(*args)
        self.assertEqual(status, 0, output)
        self.assertIn(f"0 failed, {warnings} warnings", output)
        return output

    def assertFails(self, *args, saying):
        status, output = self.project.check(*args)
        self.assertEqual(status, 1, output)
        failures = [line for line in output.splitlines() if line.startswith("FAIL")]
        self.assertTrue(
            any(saying in line for line in failures),
            f"no FAIL line containing {saying!r} in:\n{output}",
        )
        return output

    def assertCannotRun(self, *args, saying):
        status, output = self.project.check(*args)
        self.assertEqual(status, 2, output)
        self.assertIn(saying, output)

    def write_spec(self, number=1, slug="thing", **options):
        self.project.write(f"docs/specs/{number:04d}-{slug}.md", spec(number, **options))

    def build(self, number, **options):
        """Write a specification and bring it into the behaviour folder."""
        self.write_spec(number, **options)
        self.assertPasses("behaviour", "--add", number)


class SpecTests(CheckerCase):
    def test_a_complete_specification_passes(self):
        self.write_spec()
        self.assertPasses("spec", 1, warnings=1)

    def test_no_specification_for_the_issue_cannot_run(self):
        self.assertCannotRun("spec", 9, saying="no specification for issue 9")

    def test_no_config_cannot_run(self):
        (self.project.dir / ".claude/refine.json").unlink()
        self.assertCannotRun("spec", 1, saying="no .claude/refine.json")

    def test_an_unknown_status_fails(self):
        self.write_spec(status="Done")
        self.assertFails("spec", 1, saying="status is 'Done'")

    def test_a_scenario_without_an_id_fails(self):
        self.write_spec(scenarios=[scenario(1), {"id": None, "title": "untagged"}])
        self.assertFails("spec", 1, saying="scenario has no ID: untagged")

    def test_an_id_from_another_specification_fails(self):
        self.write_spec(scenarios=[scenario(1, number=7)])
        self.assertFails("spec", 1, saying="@0007-01 does not start with")

    def test_a_duplicate_id_fails(self):
        self.write_spec(scenarios=[scenario(1, "first"), scenario(1, "second")])
        self.assertFails("spec", 1, saying="@0001-01 is used more than once")

    def test_a_requirement_nothing_cites_fails(self):
        self.write_spec(requirements=["FR-1", "FR-2"])
        self.assertFails("spec", 1, saying="FR-2 is not cited")

    def test_a_requirement_cited_only_in_the_testing_strategy_passes(self):
        self.write_spec(
            requirements=["FR-1", "FR-2"], strategy_note="FR-2 is verified by reading."
        )
        self.assertPasses("spec", 1, warnings=1)

    def test_a_scenario_missing_from_the_testing_strategy_fails(self):
        self.write_spec(scenarios=[scenario(1), scenario(2, in_strategy=False)])
        self.assertFails("spec", 1, saying="@0001-02 has no entry in the testing strategy")

    def test_automated_must_be_yes_or_no(self):
        self.write_spec(scenarios=[scenario(1, automated="Partly")])
        self.assertFails("spec", 1, saying="must say Yes or No")

    def test_a_ready_specification_with_open_items_fails(self):
        self.write_spec(open_items="- Something is undecided.")
        self.assertFails("spec", 1, saying="Ready but Open items is not 'None.'")

    def test_a_draft_may_have_open_items(self):
        self.write_spec(status="Draft", open_items="- Something is undecided.")
        self.assertPasses("spec", 1, warnings=1)

    def test_a_link_that_does_not_resolve_fails(self):
        self.write_spec(decisions="[ADR 0009](../decisions/0009-missing.md)")
        self.assertFails("spec", 1, saying="link does not resolve")

    def test_a_link_that_resolves_passes(self):
        self.project.write("docs/decisions/0001-a.md", "# 0001: a\n")
        self.write_spec(decisions="[ADR 0001](../decisions/0001-a.md)")
        self.assertPasses("spec", 1, warnings=1)

    def test_no_changes_section_fails(self):
        self.write_spec(changes_title=None)
        self.assertFails("spec", 1, saying="no section 'Changes to current behaviour'")

    def test_the_earlier_name_of_the_changes_section_is_accepted(self):
        self.write_spec(changes_title="Changes to earlier specifications")
        self.assertPasses("spec", 1, warnings=1)

    def test_a_scenario_with_no_area_fails(self):
        self.write_spec(area=None)
        self.assertFails("spec", 1, saying="scenario has no area")

    def test_a_badly_formed_area_fails(self):
        self.write_spec(area="Billing/Credit Notes")
        self.assertFails("spec", 1, saying="scenario has no area, or one that is not")

    def test_a_scenario_may_name_its_own_area(self):
        self.write_spec(
            scenarios=[
                scenario(1),
                scenario(2, tags="@0001-02 @area:billing/credit-notes"),
            ]
        )
        output = self.assertPasses("spec", 1, warnings=2)
        self.assertIn("creates a new area in the behaviour folder: billing/credit-notes", output)

    def test_a_new_area_is_a_warning(self):
        self.write_spec()
        output = self.assertPasses("spec", 1, warnings=1)
        self.assertIn("WARN", output)
        self.assertIn("creates a new area in the behaviour folder: core", output)

    def test_an_existing_area_is_not_a_warning(self):
        self.build(1)
        self.write_spec(2)
        self.assertPasses("spec", 2)

    def test_listing_a_scenario_that_is_not_in_force_fails(self):
        self.write_spec(changes="- 0003-01 gone: removed.")
        self.assertFails("spec", 1, saying="@0003-01 as changed, but that scenario is not in force")

    def test_listing_a_scenario_that_is_in_force_passes(self):
        self.build(1)
        self.write_spec(2, changes="- 0001-01 scenario 1: replaced by 0002-01.")
        self.assertPasses("spec", 2)

    def test_a_built_specification_is_not_held_to_what_it_retired(self):
        self.build(1)
        self.build(2, changes="- 0001-01 scenario 1: replaced by 0002-01.")
        self.assertPasses("spec", 2)

    def test_citing_a_convention_that_does_not_exist_fails(self):
        self.write_spec(assumptions="- Settled by convention: C-4.")
        self.assertFails("spec", 1, saying="cites C-4")

    def test_citing_a_convention_that_exists_passes(self):
        self.project.write("docs/specs/CONVENTIONS.md", "| C-4 | A rule | 2026-01-01 |\n")
        self.write_spec(assumptions="- Settled by convention: C-4.")
        self.assertPasses("spec", 1, warnings=1)

    def test_citing_a_standard_that_does_not_exist_fails(self):
        self.write_spec(design="Standards applied: S-DB-9.")
        self.assertFails("spec", 1, saying="cites S-DB-9")

    def test_citing_a_standard_that_exists_passes(self):
        self.project.write(
            "docs/standards/database.md",
            "# Database\n\nApplies to: `src/**`\n\n| S-DB-9 | A rule | |\n",
        )
        self.write_spec(design="Standards applied: S-DB-9.")
        self.assertPasses("spec", 1, warnings=1)


class AutoAcceptTests(CheckerCase):
    MARK = "Accepted under the auto-accept policy on 2026-01-01: no assumption was made."

    def setUp(self):
        super().setUp()
        self.project.config({"process": {"autoAccept": True}})
        self.build(1)

    def test_a_specification_that_left_nothing_to_review_passes(self):
        self.write_spec(2, assumptions=self.MARK)
        self.assertPasses("spec", 2)

    def test_conventions_relied_on_do_not_count_as_assumptions(self):
        self.project.write("docs/specs/CONVENTIONS.md", "| C-1 | A rule | 2026-01-01 |\n")
        self.write_spec(2, assumptions=f"{self.MARK}\n\n- Settled by convention: C-1.")
        self.assertPasses("spec", 2)

    def test_it_fails_when_the_policy_is_off(self):
        self.project.config({})
        self.write_spec(2, assumptions=self.MARK)
        self.assertFails("spec", 2, saying="process.autoAccept is not on")

    def test_it_fails_when_an_assumption_is_listed(self):
        self.write_spec(2, assumptions=f"{self.MARK}\n\n- The error is a ValueError.")
        self.assertFails("spec", 2, saying="lists 1 assumptions that nobody has reviewed")

    def test_it_fails_when_it_changes_behaviour_in_force(self):
        self.write_spec(
            2, assumptions=self.MARK, changes="- 0001-01 scenario 1: removed."
        )
        self.assertFails("spec", 2, saying="changes behaviour in force")

    def test_it_fails_when_it_creates_a_new_area(self):
        self.write_spec(2, assumptions=self.MARK, area="somewhere-new")
        self.assertFails("spec", 2, saying="creates a new area")


class TestsCheckTests(CheckerCase):
    def setUp(self):
        super().setUp()
        self.write_spec(1, scenarios=[scenario(1), scenario(2)])
        self.project.write(
            "tests/test_thing.py",
            test_file(["0001-01", "0001-02"], untagged="LEGACY = 1\n"),
        )
        self.project.commit()

    def add_second_spec(self, **options):
        self.write_spec(2, scenarios=[scenario(1, number=2)], **options)

    def rewrite_tests(self, ids, **options):
        options.setdefault("untagged", "LEGACY = 1\n")
        self.project.write("tests/test_thing.py", test_file(ids, **options))

    def test_every_scenario_carried_by_a_test_passes(self):
        self.assertPasses("tests", 1)

    def test_a_scenario_with_no_test_fails(self):
        self.add_second_spec()
        self.assertFails("tests", 2, saying="@0002-01 is not carried by any test")

    def test_a_specification_without_ids_cannot_run(self):
        self.write_spec(3, scenarios=[{"id": None, "title": "old"}])
        self.assertCannotRun("tests", 3, saying="has no scenario IDs")

    def test_the_behaviour_folder_does_not_count_as_a_test(self):
        # Its files carry every scenario ID in force, but they are documents.
        self.add_second_spec()
        self.assertPasses("behaviour", "--add", 2)
        self.assertFails("tests", 2, saying="@0002-01 is not carried by any test")

    def test_a_test_carrying_an_unknown_id_fails(self):
        self.rewrite_tests(["0001-01", "0001-02", "0007-09"])
        self.assertFails("tests", 1, saying="@0007-09 in tests/test_thing.py is not a scenario")

    def test_adding_tests_for_a_new_specification_passes(self):
        self.add_second_spec()
        self.rewrite_tests(["0001-01", "0001-02", "0002-01"])
        self.assertPasses("tests", 2)

    def test_changing_another_scenarios_test_fails(self):
        self.add_second_spec()
        self.rewrite_tests(
            ["0001-01", "0001-02", "0002-01"], bodies={"0001-02": "assert 1 + 1 == 2"}
        )
        self.assertFails("tests", 2, saying="the test for @0001-02 was changed")

    def test_a_change_hidden_from_a_line_diff_is_still_caught(self):
        # Git shows this edit as an insertion, because the old line reappears
        # in the test added below it.
        self.add_second_spec()
        self.rewrite_tests(
            ["0001-01", "0001-02", "0002-01"], bodies={"0001-02": "assert 2 == 2"}
        )
        self.assertFails("tests", 2, saying="the test for @0001-02 was changed")

    def test_changing_a_test_the_specification_lists_passes(self):
        self.add_second_spec(changes="- 0001-02 scenario 2: replaced by 0002-01.")
        self.rewrite_tests(
            ["0001-01", "0001-02", "0002-01"], bodies={"0001-02": "assert 1 + 1 == 2"}
        )
        self.assertPasses("tests", 2)

    def test_removing_another_scenarios_test_fails(self):
        self.add_second_spec()
        self.rewrite_tests(["0001-02", "0002-01"])
        self.assertFails("tests", 2, saying="the test for @0001-01 was removed")

    def test_removing_a_test_the_specification_lists_passes(self):
        self.add_second_spec(changes="- 0001-01 scenario 1: removed.")
        self.rewrite_tests(["0001-02", "0002-01"])
        self.assertPasses("tests", 2)

    def test_deleting_a_test_file_fails_for_each_scenario_in_it(self):
        self.add_second_spec()
        (self.project.dir / "tests/test_thing.py").unlink()
        self.project.write("tests/test_other.py", test_file(["0002-01"]))
        self.assertFails("tests", 2, saying="the test for @0001-01 was removed")

    def test_changing_test_code_with_no_id_is_a_warning(self):
        self.rewrite_tests(["0001-01", "0001-02"], untagged="LEGACY = 2\n")
        output = self.assertPasses("tests", 1, warnings=1)
        self.assertIn("existing test code with no scenario ID was changed", output)

    def test_new_tests_may_go_above_a_trailing_main_guard(self):
        guard = 'if __name__ == "__main__":\n    unittest.main()\n'
        self.rewrite_tests(["0001-01", "0001-02"], tail=guard)
        self.project.commit()
        self.add_second_spec()
        self.rewrite_tests(["0001-01", "0001-02", "0002-01"], tail=guard)
        self.assertPasses("tests", 2)

    def test_a_scenario_verified_by_hand_needs_no_test(self):
        self.write_spec(2, scenarios=[scenario(1, number=2, automated="No")])
        output = self.assertPasses("tests", 2, warnings=1)
        self.assertIn("@0002-01 is verified by hand", output)

    def test_changes_to_documents_are_ignored(self):
        self.write_spec(1, scenarios=[scenario(1), scenario(2)], design="Reworded.")
        self.assertPasses("tests", 1)


class RedGreenTests(CheckerCase):
    def setUp(self):
        super().setUp()
        self.write_spec(1, scenarios=[scenario(1), scenario(2)])
        self.project.write("src/thing.py", "VALUE = 1\n")
        self.project.commit()

    def write_tests(self, **options):
        self.project.write("tests/test_thing.py", test_file(["0001-01", "0001-02"], **options))

    def test_red_fails_while_a_scenario_has_no_test(self):
        self.assertFails("red", 1, "--", *FAILING, saying="@0001-01 has no test yet")

    def test_red_fails_when_the_suite_already_passes(self):
        self.write_tests()
        self.assertFails("red", 1, "--", *PASSING, saying="the suite passed before the code")

    def test_red_records_a_failing_run(self):
        self.write_tests()
        output = self.assertPasses("red", 1, "--", *FAILING)
        self.assertIn("recorded: 2 tests", output)
        self.assertTrue((self.project.dir / ".git/backlog/0001.json").is_file())

    def test_red_without_a_command_cannot_run(self):
        self.write_tests()
        self.assertCannotRun("red", 1, saying="give the test command")

    def test_green_fails_with_no_failing_run_recorded(self):
        self.write_tests()
        self.assertFails("green", 1, "--", *PASSING, saying="there is no record of the tests")

    def test_green_fails_while_the_suite_fails(self):
        self.write_tests()
        self.assertPasses("red", 1, "--", *FAILING)
        self.assertFails("green", 1, "--", *FAILING, saying="the suite failed")

    def test_green_passes_after_red(self):
        self.write_tests()
        self.assertPasses("red", 1, "--", *FAILING)
        self.assertPasses("green", 1, "--", *PASSING)

    def test_green_warns_when_a_test_was_edited_after_red(self):
        self.write_tests()
        self.assertPasses("red", 1, "--", *FAILING)
        self.write_tests(bodies={"0001-02": "assert not False"})
        output = self.assertPasses("green", 1, "--", *PASSING, warnings=1)
        self.assertIn("the test for @0001-02 was changed after it was seen to fail", output)

    def test_green_fails_when_red_was_recorded_against_another_commit(self):
        self.write_tests()
        self.assertPasses("red", 1, "--", *FAILING)
        self.project.commit()
        self.assertFails("green", 1, "--", *PASSING, saying="recorded against commit")

    def test_a_specification_with_no_automated_scenario_has_nothing_to_run(self):
        self.write_spec(
            1, scenarios=[scenario(1, automated="No"), scenario(2, automated="No")]
        )
        status, output = self.project.check("red", 1)
        self.assertEqual(status, 0, output)
        self.assertIn("nothing to record", output)
        status, output = self.project.check("green", 1)
        self.assertEqual(status, 0, output)
        self.assertIn("nothing to run", output)

    def test_only_automated_scenarios_need_a_test_before_red(self):
        self.write_spec(1, scenarios=[scenario(1), scenario(2, automated="No")])
        self.project.write("tests/test_thing.py", test_file(["0001-01"]))
        self.assertPasses("red", 1, "--", *FAILING)


class BaselineTests(CheckerCase):
    """A baseline ties existing tests to scenarios and changes nothing else."""

    UNTAGGED = "def test_one():\n    assert True\n\n\ndef test_two():\n    assert True\n"
    TAGGED = (
        "# @0001-01\ndef test_one():\n    assert True\n\n\n"
        "# @0001-02\ndef test_two():\n    assert True\n"
    )

    def setUp(self):
        super().setUp()
        self.write_spec(1, scenarios=[scenario(1), scenario(2)])
        self.project.write("tests/test_thing.py", self.UNTAGGED)
        self.project.commit()

    def test_a_passing_suite_is_accepted_when_only_ids_were_added(self):
        self.project.write("tests/test_thing.py", self.TAGGED)
        output = self.assertPasses("red", 1, "--", *PASSING)
        self.assertIn("baseline", output)
        self.assertPasses("green", 1, "--", *PASSING)
        self.assertPasses("tests", 1)

    def test_it_is_refused_when_a_test_body_also_changed(self):
        self.project.write(
            "tests/test_thing.py", self.TAGGED.replace("assert True", "assert 1")
        )
        self.assertFails("red", 1, "--", *PASSING, saying="the suite passed before the code")

    def test_it_is_refused_when_a_test_was_added(self):
        self.project.write(
            "tests/test_thing.py",
            self.TAGGED + "\n\ndef test_three():\n    assert True\n",
        )
        self.assertFails("red", 1, "--", *PASSING, saying="the suite passed before the code")

    def test_it_is_refused_when_a_new_file_was_added(self):
        self.project.write("tests/test_thing.py", self.TAGGED)
        self.project.write("src/new.py", "VALUE = 1\n")
        self.assertFails("red", 1, "--", *PASSING, saying="the suite passed before the code")


class BehaviourTests(CheckerCase):
    def area(self, name):
        return self.project.read(f"docs/behaviour/{name}.md")

    def index(self):
        return self.project.read("docs/behaviour/README.md")

    def test_no_folder_yet_is_not_a_failure(self):
        output = self.assertPasses("behaviour")
        self.assertIn("no behaviour folder yet", output)

    def test_adding_a_specification_writes_its_area_and_the_index(self):
        self.build(1, scenarios=[scenario(1, "first"), scenario(2, "second")])
        self.assertIn("@0001-01", self.area("core"))
        self.assertIn("Scenario: second", self.area("core"))
        self.assertIn("| [core](core.md) | 2 | 0001 |", self.index())
        self.assertIn("Specifications included: 0001", self.index())
        self.assertPasses("behaviour")

    def test_a_specification_without_ids_cannot_be_added(self):
        self.write_spec(1, scenarios=[{"id": None, "title": "old"}])
        self.assertCannotRun("behaviour", "--add", 1, saying="has no scenario IDs")

    def test_scenarios_are_filed_under_their_own_area(self):
        self.build(
            1,
            scenarios=[
                scenario(1),
                scenario(2, tags="@0001-02 @area:billing/credit-notes"),
            ],
        )
        self.assertIn("@0001-01", self.area("core"))
        self.assertNotIn("@0001-02", self.area("core"))
        self.assertIn("@0001-02", self.area("billing/credit-notes"))

    def test_a_later_specification_adds_to_an_area(self):
        self.build(1)
        self.build(2)
        self.assertIn("@0001-01", self.area("core"))
        self.assertIn("@0002-01", self.area("core"))
        self.assertIn("| [core](core.md) | 2 | 0002 |", self.index())
        self.assertIn("Specifications included: 0001, 0002", self.index())

    def test_a_replaced_scenario_is_dropped(self):
        self.build(1, scenarios=[scenario(1), scenario(2)])
        self.build(2, changes="- 0001-02 scenario 2: replaced by 0002-01.")
        self.assertIn("@0001-01", self.area("core"))
        self.assertNotIn("@0001-02", self.area("core"))
        self.assertIn("@0002-01", self.area("core"))

    def test_an_area_left_empty_is_removed(self):
        self.build(1, area="old-area")
        self.build(2, changes="- 0001-01 scenario 1: removed.")
        self.assertFalse((self.project.dir / "docs/behaviour/old-area.md").exists())
        self.assertNotIn("old-area", self.index())
        self.assertPasses("behaviour")

    def test_steps_notes_and_examples_are_kept(self):
        self.build(
            1,
            scenarios=[
                scenario(
                    1,
                    "small amounts",
                    keyword="Scenario Outline",
                    steps=[
                        "When I use <net>",
                        "# a note",
                        "Then I get <vat>",
                        "",
                        "Examples:",
                        "| net | vat |",
                        "| 2   | 0   |",
                    ],
                )
            ],
        )
        text = self.area("core")
        for expected in (
            "Scenario Outline: small amounts",
            "When I use <net>",
            "# a note",
            "Examples:",
            "| 2   | 0   |",
        ):
            self.assertIn(expected, text)

    def test_the_requirement_comment_above_a_scenario_is_left_out(self):
        self.build(1)
        self.assertNotIn("# FR-1", self.area("core"))

    def test_adding_twice_changes_nothing(self):
        self.build(1)
        before = self.area("core"), self.index()
        self.assertPasses("behaviour", "--add", 1)
        self.assertEqual(before, (self.area("core"), self.index()))

    def test_an_edit_by_hand_fails(self):
        self.build(1)
        self.project.write("docs/behaviour/core.md", self.area("core") + "\nextra\n")
        self.assertFails("behaviour", saying="differs from what the specifications generate")

    def test_a_file_nothing_generated_fails(self):
        self.build(1)
        self.project.write("docs/behaviour/notes.md", "stray\n")
        self.assertFails("behaviour", saying="notes.md: not generated")


class StandardsTests(CheckerCase):
    def topic(self, name, applies, *rules):
        lines = [f"# {name}", ""]
        if applies:
            lines += [f"Applies to: {applies}", ""]
        lines += ["| No. | Rule | Why |", "|-----|------|-----|"]
        lines += [f"| {rule} | A rule | |" for rule in rules]
        self.project.write(f"docs/standards/{name.lower()}.md", "\n".join(lines) + "\n")

    def test_no_standards_is_not_a_failure(self):
        output = self.assertPasses("standards")
        self.assertIn("no standards yet", output)

    def test_topics_are_listed_with_what_they_apply_to(self):
        self.topic("Database", "`src/**/*.py`", "S-DB-1", "S-DB-2")
        output = self.assertPasses("standards")
        self.assertIn("docs/standards/database.md", output)
        self.assertIn("applies to: `src/**/*.py`", output)
        self.assertIn("rules: 2", output)

    def test_a_topic_that_does_not_say_what_it_applies_to_fails(self):
        self.topic("CSS", None, "S-CSS-1")
        self.assertFails("standards", saying="no 'Applies to:' line")

    def test_a_rule_number_used_twice_fails(self):
        self.topic("Database", "`src/**`", "S-DB-1")
        self.topic("CSS", "`web/**`", "S-DB-1")
        self.assertFails("standards", saying="S-DB-1 is also in")


class VerifyTests(CheckerCase):
    OK = f'"{sys.executable}" -c "print(\'ran the check\')"'
    BROKEN = f'"{sys.executable}" -c "import sys; sys.exit(3)"'

    def setUp(self):
        super().setUp()
        self.project.write("src/a.py", "VALUE = 1\n")
        self.project.write("web/site.css", "a {}\n")
        self.project.commit()

    def verify(self, *entries):
        self.project.config({"implement": {"verify": list(entries)}})
        self.project.git("add", "-A")
        self.project.git("commit", "-q", "-m", "config")

    def test_nothing_configured_is_not_a_failure(self):
        output = self.assertPasses("verify")
        self.assertIn("no checks configured", output)

    def test_a_check_with_no_paths_always_runs(self):
        self.verify(self.OK)
        output = self.assertPasses("verify")
        self.assertIn("ran the check", output)

    def test_a_failing_check_fails(self):
        self.verify(self.BROKEN)
        self.assertFails("verify", saying="failed with exit status 3")

    def test_a_check_is_skipped_when_no_changed_file_matches(self):
        self.verify({"run": self.BROKEN, "when": ["web/**"]})
        self.project.write("src/a.py", "VALUE = 2\n")
        output = self.assertPasses("verify")
        self.assertIn("skipped", output)

    def test_a_check_runs_when_a_changed_file_matches(self):
        self.verify({"run": self.BROKEN, "when": ["web/**"]})
        self.project.write("web/site.css", "a { color: red }\n")
        self.assertFails("verify", saying="failed with exit status 3")

    def test_a_new_file_counts_as_changed(self):
        self.verify({"run": self.BROKEN, "when": ["web/**"]})
        self.project.write("web/new.css", "b {}\n")
        self.assertFails("verify", saying="failed with exit status 3")

    def test_standards_covering_a_changed_file_are_named(self):
        self.project.write(
            "docs/standards/css.md", "# CSS\n\nApplies to: `web/**`\n\n| S-CSS-1 | A rule | |\n"
        )
        self.verify(self.OK)
        self.project.write("web/site.css", "a { color: red }\n")
        output = self.assertPasses("verify")
        self.assertIn("standards that apply to 1 changed file(s): docs/standards/css.md", output)

    def test_an_entry_with_no_command_cannot_run(self):
        self.verify({"when": ["web/**"]})
        self.assertCannotRun("verify", saying="has no command")


class ClosedTests(CheckerCase):
    def setUp(self):
        super().setUp()
        self.project.write("docs/decisions/0001-a.md", "# 0001: a\n")
        self.write_spec(decisions="[ADR 0001](../decisions/0001-a.md)")
        self.project.commit(date="2026-01-01T10:00:00+00:00")
        self.project.issues(
            [{"number": 1, "state": "CLOSED", "closedAt": "2026-01-02T00:00:00Z"}]
        )

    def test_work_untouched_since_its_issue_closed_passes(self):
        self.assertPasses("closed")

    def test_a_specification_changed_after_its_issue_closed_fails(self):
        self.write_spec(
            decisions="[ADR 0001](../decisions/0001-a.md)", design="Reworded later."
        )
        self.project.commit(date="2026-01-03T10:00:00+00:00")
        self.assertFails("closed", saying="belongs to closed issue #1 but was changed")

    def test_an_adr_changed_after_its_issue_closed_fails(self):
        self.project.write("docs/decisions/0001-a.md", "# 0001: a, reconsidered\n")
        self.project.commit(date="2026-01-03T10:00:00+00:00")
        self.assertFails("closed", saying="docs/decisions/0001-a.md: belongs to closed issue #1")

    def test_an_uncommitted_change_to_closed_work_fails(self):
        self.write_spec(
            decisions="[ADR 0001](../decisions/0001-a.md)", design="Not yet committed."
        )
        self.assertFails("closed", saying="has uncommitted changes")

    def test_an_open_issue_may_still_be_edited(self):
        self.write_spec(2)
        self.project.commit(date="2026-01-03T10:00:00+00:00")
        self.write_spec(2, design="Still being refined.")
        self.assertPasses("closed")

    def test_github_failing_cannot_run(self):
        self.project.env["FAKE_GH_ISSUES"] = str(self.project.dir / "missing.json")
        self.assertCannotRun("closed", saying="gh issue list")


class StateTests(CheckerCase):
    def issue(self, number=1, state="OPEN", labels=("ready",), status="Ready", link=True):
        name = f"{number:04d}-thing.md"
        body = "## Specification\n\n"
        body += f"[docs/specs/{name}](https://example.com/{name})\n\n" if link else ""
        body += f"Status: **{status}**\n" if status else ""
        return {
            "number": number,
            "state": state,
            "closedAt": "2026-01-02T00:00:00Z" if state == "CLOSED" else None,
            "labels": [{"name": label} for label in labels],
            "body": body,
        }

    def index(self, *rows):
        self.project.write(
            "docs/specs/README.md",
            "# Features\n\n" + "".join(f"| {row} |\n" for row in rows),
        )

    def setUp(self):
        super().setUp()
        self.write_spec()
        self.index("0001 | [Thing](0001-thing.md) | Ready | #1")

    def test_an_open_issue_that_agrees_with_its_specification_passes(self):
        self.project.issues([self.issue()])
        self.assertPasses("state")

    def test_a_specification_with_no_issue_fails(self):
        self.project.issues([])
        self.assertFails("state", saying="there is no issue #1")

    def test_a_ready_specification_without_the_label_fails(self):
        self.project.issues([self.issue(labels=())])
        self.assertFails("state", saying="does not have the 'ready' label")

    def test_a_draft_specification_with_the_label_fails(self):
        self.write_spec(status="Draft")
        self.index("0001 | [Thing](0001-thing.md) | Draft | #1")
        self.project.issues([self.issue(status="Draft")])
        self.assertFails("state", saying="has the 'ready' label")

    def test_labels_are_left_alone_when_none_is_configured(self):
        self.project.config({"finalise": {"readyLabel": ""}})
        self.project.issues([self.issue(labels=())])
        self.assertPasses("state")

    def test_an_issue_that_does_not_link_to_its_specification_fails(self):
        self.project.issues([self.issue(link=False)])
        self.assertFails("state", saying="issue #1 does not link to it")

    def test_an_issue_stating_another_status_fails(self):
        self.project.issues([self.issue(status="Draft")])
        self.assertFails("state", saying="issue #1 says Draft")

    def test_a_specification_missing_from_the_index_fails(self):
        self.index()
        self.project.issues([self.issue()])
        self.assertFails("state", saying="not listed in docs/specs/README.md")

    def test_an_index_showing_another_status_fails(self):
        self.index("0001 | [Thing](0001-thing.md) | Draft | #1")
        self.project.issues([self.issue()])
        self.assertFails("state", saying="shows something else")

    def test_a_closed_issue_with_a_draft_specification_fails(self):
        self.write_spec(status="Draft")
        self.index("0001 | [Thing](0001-thing.md) | Draft | #1")
        self.project.issues([self.issue(state="CLOSED", status="Draft")])
        self.assertFails("state", saying="is closed but the specification is Draft")

    def test_a_closed_issue_missing_from_the_behaviour_folder_fails(self):
        self.project.write("tests/test_thing.py", test_file(["0001-01"]))
        self.project.issues([self.issue(state="CLOSED")])
        self.assertFails("state", saying="is not in docs/behaviour")

    def test_a_closed_issue_with_a_scenario_no_test_carries_fails(self):
        self.assertPasses("behaviour", "--add", 1)
        self.project.issues([self.issue(state="CLOSED")])
        self.assertFails("state", saying="@0001-01 is carried by no test")

    def test_a_closed_issue_that_is_built_and_tested_passes(self):
        self.assertPasses("behaviour", "--add", 1)
        self.project.write("tests/test_thing.py", test_file(["0001-01"]))
        self.project.issues([self.issue(state="CLOSED")])
        self.assertPasses("state")

    def test_a_closed_issue_need_not_test_a_scenario_later_retired(self):
        self.assertPasses("behaviour", "--add", 1)
        self.build(2, changes="- 0001-01 scenario 1: replaced by 0002-01.")
        self.index(
            "0001 | [Thing](0001-thing.md) | Ready | #1",
            "0002 | [Thing](0002-thing.md) | Ready | #2",
        )
        self.project.write("tests/test_thing.py", test_file(["0002-01"]))
        self.project.issues(
            [self.issue(state="CLOSED"), self.issue(number=2, state="CLOSED")]
        )
        self.assertPasses("state")

    def test_a_closed_issue_need_not_test_a_scenario_verified_by_hand(self):
        self.write_spec(scenarios=[scenario(1, automated="No")])
        self.assertPasses("behaviour", "--add", 1)
        self.project.issues([self.issue(state="CLOSED")])
        self.assertPasses("state")

    def test_a_specification_written_before_ids_is_not_expected_in_the_folder(self):
        self.write_spec(scenarios=[{"id": None, "title": "old"}])
        self.project.issues([self.issue(state="CLOSED")])
        self.assertPasses("state")


class PathPatternTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loaded = importlib.util.spec_from_file_location("backlog_check", CHECKER)
        cls.checker = importlib.util.module_from_spec(loaded)
        sys.dont_write_bytecode = True
        loaded.loader.exec_module(cls.checker)

    def test_patterns(self):
        cases = [
            ("a/b.py", "**/*.py", True),
            ("b.py", "**/*.py", True),
            ("web/x/y.css", "web/**", True),
            ("web.css", "web/**", False),
            ("src/a.py", "src/*.py", True),
            ("src/x/a.py", "src/*.py", False),
            ("a.css", "*.css", True),
            ("x/a.css", "*.css", False),
            ("src/a.py", "src/?.py", True),
            ("src/ab.py", "src/?.py", False),
            ("a+b.py", "a+b.py", True),
        ]
        for path, pattern, expected in cases:
            with self.subTest(path=path, pattern=pattern):
                self.assertEqual(self.checker.matches(path, [pattern]), expected)


if __name__ == "__main__":
    unittest.main()
