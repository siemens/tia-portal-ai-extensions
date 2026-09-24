import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "validate_skills.py"
SPEC = importlib.util.spec_from_file_location("validate_skills", SCRIPT_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VALIDATOR)


class ValidateSkillsTests(unittest.TestCase):
    def setUp(self):
        self.original_root = VALIDATOR.ROOT
        self.temp_directory = tempfile.TemporaryDirectory()
        VALIDATOR.ROOT = Path(self.temp_directory.name)

    def tearDown(self):
        VALIDATOR.ROOT = self.original_root
        self.temp_directory.cleanup()

    def write(self, relative_path: str, content: str) -> Path:
        path = VALIDATOR.ROOT / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    def write_skill(
        self,
        name: str,
        *,
        dependencies: str = "",
        body: str = "# Example\n",
    ) -> Path:
        dependency_metadata = (
            "metadata:\n"
            f'  {VALIDATOR.DEPENDENCY_METADATA_KEY}: "{dependencies}"\n'
            if dependencies
            else ""
        )
        return self.write(
            f"skills/{name}/SKILL.md",
            (
                "---\n"
                f"name: {name}\n"
                f"description: Description for {name}.\n"
                f"{dependency_metadata}"
                "---\n\n"
                f"{body}"
            ),
        )

    def write_manifests(self) -> None:
        manifest = {
            "$schema": VALIDATOR.PORTABLE_SCHEMA,
            "name": VALIDATOR.EXPECTED_PLUGIN_NAME,
            "description": "Example plugin.",
            "version": VALIDATOR.EXPECTED_PLUGIN_VERSION,
            "author": {"name": "Example Team"},
            "license": "MIT",
            "keywords": ["example"],
        }
        self.write("plugin.json", json.dumps(manifest))
        self.write(
            ".github/plugin/marketplace.json",
            json.dumps(
                {
                    "name": VALIDATOR.EXPECTED_MARKETPLACE_NAME,
                    "owner": {"name": "Example Team"},
                    "plugins": [{**manifest, "source": "."}],
                }
            ),
        )

    def run_main(self) -> int:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return VALIDATOR.main()

    def test_nested_metadata_is_accepted(self):
        skill_path = self.write(
            "skills/example-skill/SKILL.md",
            "---\n"
            "name: example-skill\n"
            "description: Example description.\n"
            "metadata:\n"
            "  author: example-org\n"
            "  version: 1.0.0\n"
            "---\n\n"
            "# Example\n",
        )

        errors = []
        frontmatter, _ = VALIDATOR.parse_frontmatter(skill_path, errors)

        self.assertEqual([], errors)
        self.assertEqual(
            {"author": "example-org", "version": "1.0.0"},
            frontmatter["metadata"],
        )

    def test_nonstandard_top_level_frontmatter_is_an_error(self):
        self.write(
            "skills/example-skill/SKILL.md",
            "---\n"
            "name: example-skill\n"
            "description: Example description.\n"
            "depends_on: [other-skill]\n"
            "---\n\n"
            "# Example\n",
        )
        errors = []

        VALIDATOR.validate_skills(errors, [], expected_skills=None)

        self.assertTrue(
            any("unsupported skill frontmatter fields: depends_on" in error for error in errors),
            errors,
        )

    def test_links_inside_code_are_ignored(self):
        skill_path = self.write("skills/example-skill/SKILL.md", "")
        errors = []
        VALIDATOR.validate_links(
            skill_path,
            "```powershell\n$value = [Math]::Max($left, $right)\n```\n"
            "`[inline](not-a-link)`",
            errors,
        )

        self.assertEqual([], errors)

    def test_zero_skills_is_an_error(self):
        errors = []
        VALIDATOR.validate_skills(errors, [], expected_skills=None)

        self.assertIn(
            "no Agent Skills found under skills/*/SKILL.md",
            errors,
        )
        self.assertNotEqual(0, self.run_main())

    def test_missing_manifest_is_an_error(self):
        for name in VALIDATOR.EXPECTED_SKILLS:
            self.write_skill(name)
        errors = []
        VALIDATOR.validate_manifests(errors)

        self.assertIn(
            "missing root Agent Plugins manifest: plugin.json",
            errors,
        )
        self.assertNotEqual(0, self.run_main())

    def test_missing_approved_skill_returns_nonzero(self):
        missing = next(iter(VALIDATOR.EXPECTED_SKILLS))
        for name in VALIDATOR.EXPECTED_SKILLS - {missing}:
            self.write_skill(name)
        self.write_manifests()

        self.assertNotEqual(0, self.run_main())

    def test_malformed_manifest_is_an_error(self):
        for name in VALIDATOR.EXPECTED_SKILLS:
            self.write_skill(name)
        self.write("plugin.json", "{")
        errors = []
        VALIDATOR.validate_manifests(errors)

        self.assertTrue(
            any("invalid JSON" in error for error in errors),
            errors,
        )
        self.assertNotEqual(0, self.run_main())

    def test_broken_link_is_an_error(self):
        for name in VALIDATOR.EXPECTED_SKILLS:
            self.write_skill(name)
        self.write_manifests()
        self.write("README.md", "[Missing](missing.md)\n")
        errors = []
        VALIDATOR.validate_documents(errors)

        self.assertTrue(
            any("broken relative link" in error for error in errors),
            errors,
        )
        self.assertNotEqual(0, self.run_main())

    def test_missing_dependency_is_an_error(self):
        for name in VALIDATOR.EXPECTED_SKILLS:
            self.write_skill(
                name,
                dependencies="missing-skill" if name == "blocks" else "",
            )
        self.write_manifests()
        errors = []
        VALIDATOR.validate_skills(errors, [])

        self.assertTrue(
            any("unknown dependency 'missing-skill'" in error for error in errors),
            errors,
        )
        self.assertNotEqual(0, self.run_main())

    def test_invalid_skill_frontmatter_does_not_crash(self):
        self.write(
            "skills/example-skill/SKILL.md",
            (
                "---\n"
                "description: Example description.\n"
                "metadata:\n"
                f'  {VALIDATOR.DEPENDENCY_METADATA_KEY}: "missing-skill"\n'
                "---\n"
            ),
        )
        errors = []

        VALIDATOR.validate_skills(errors, [], expected_skills=None)

        self.assertTrue(
            any("invalid or missing skill name" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("unknown dependency" in error for error in errors),
            errors,
        )

    def test_dependency_cycle_is_an_error(self):
        self.write_skill("first-skill", dependencies="second-skill")
        self.write_skill("second-skill", dependencies="first-skill")
        errors = []
        VALIDATOR.validate_skills(errors, [], expected_skills=None)

        self.assertTrue(
            any("dependency cycle:" in error for error in errors),
            errors,
        )

    def test_marketplace_metadata_must_match_manifest(self):
        self.write_manifests()
        marketplace_path = VALIDATOR.ROOT / ".github" / "plugin" / "marketplace.json"
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        marketplace["plugins"][0]["version"] = "2.0.0"
        marketplace_path.write_text(
            json.dumps(marketplace),
            encoding="utf-8",
            newline="\n",
        )
        errors = []
        VALIDATOR.validate_manifests(errors)

        self.assertTrue(
            any("plugin version differs" in error for error in errors),
            errors,
        )

    def test_valid_minimal_repository_passes(self):
        self.write_skill("example-skill")
        self.write_manifests()
        errors = []
        warnings = []

        VALIDATOR.validate_skills(
            errors,
            warnings,
            expected_skills=None,
        )
        VALIDATOR.validate_manifests(errors)
        VALIDATOR.validate_documents(errors)

        self.assertEqual([], errors)
        self.assertEqual([], warnings)


if __name__ == "__main__":
    unittest.main()
