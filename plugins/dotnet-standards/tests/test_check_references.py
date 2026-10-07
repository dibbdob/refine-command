import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from check_references import check  # noqa: E402

STANDARD = (
    "# Topic\n\nApplies to: `**/*.cs`\n\n"
    "Before designing or writing anything this covers, load the "
    "`dotnet-standards:{skill}` skill.{extra}\n\n"
    "| No. | Rule | Why |\n|-----|------|-----|\n| {rule} | A rule. | |\n"
)


class CheckReferences(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "standards").mkdir()
        self.addCleanup(self.tmp.cleanup)

    def standard(self, file, skill, rule="S-A-1", connector=None):
        extra = (
            f" Look it up with the `{connector}` connector of the "
            "dotnet-standards plugin."
            if connector
            else ""
        )
        (self.root / "standards" / file).write_text(
            STANDARD.format(skill=skill, rule=rule, extra=extra)
        )

    def connector(self, name):
        (self.root / ".mcp.json").write_text(
            json.dumps({"mcpServers": {name: {"type": "http", "url": "https://x"}}})
        )

    def skill(self, folder, name):
        path = self.root / "skills" / folder
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(f"---\nname: {name}\n---\n\n# Body\n")

    def test_a_standard_and_its_skill_pass(self):
        self.standard("a.md", "alpha")
        self.skill("alpha", "alpha")
        self.assertEqual(check(self.root), [])

    def test_a_skill_is_known_by_its_folder_not_its_header(self):
        self.standard("a.md", "header-name")
        self.skill("folder-name", "header-name")
        found = check(self.root)
        self.assertIn("'header-name', which is not in this plugin", found[0])
        self.assertIn("'folder-name', which no standard refers to", found[1])

    def test_a_connector_a_standard_refers_to_passes(self):
        self.standard("a.md", "alpha", connector="docs")
        self.skill("alpha", "alpha")
        self.connector("docs")
        self.assertEqual(check(self.root), [])

    def test_a_connector_no_standard_refers_to_fails(self):
        self.standard("a.md", "alpha")
        self.skill("alpha", "alpha")
        self.connector("docs")
        self.assertIn("'docs', which no standard refers to", check(self.root)[0])

    def test_a_standard_naming_a_missing_connector_fails(self):
        self.standard("a.md", "alpha", connector="docs")
        self.skill("alpha", "alpha")
        self.assertIn("connector 'docs', which is not in this plugin", check(self.root)[0])

    def test_a_standard_naming_a_missing_skill_fails(self):
        self.standard("a.md", "alpha")
        self.assertIn("which is not in this plugin", check(self.root)[0])

    def test_a_skill_no_standard_refers_to_fails(self):
        self.standard("a.md", "alpha")
        self.skill("alpha", "alpha")
        self.skill("beta", "beta")
        self.assertIn("which no standard refers to", check(self.root)[0])

    def test_a_standard_naming_no_skill_fails(self):
        (self.root / "standards" / "a.md").write_text("# Topic\n")
        self.assertIn("names no skill", check(self.root)[0])

    def test_a_rule_number_used_twice_fails(self):
        self.standard("a.md", "alpha")
        self.standard("b.md", "alpha")
        self.skill("alpha", "alpha")
        self.assertIn("is in both", check(self.root)[0])


if __name__ == "__main__":
    unittest.main()
