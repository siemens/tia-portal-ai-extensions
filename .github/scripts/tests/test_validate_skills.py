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
        package: str = "openness_development",
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
            f"{package}/skills/{name}/SKILL.md",
            (
                "---\n"
                f"name: {name}\n"
                f"description: Description for {name}.\n"
                f"{dependency_metadata}"
                "---\n\n"
                f"{body}"
            ),
        )

    def write_approved_openness_skills(self, *, missing: str | None = None) -> None:
        expected = VALIDATOR.EXPECTED_SKILLS_BY_PLUGIN["openness_development"]
        for name in expected - ({missing} if missing else set()):
            self.write_skill(name)

    def write_manifests(
        self,
        package: str = "openness_development",
        *,
        plugin_name: str | None = None,
    ) -> None:
        if plugin_name is None:
            plugin_name = VALIDATOR.EXPECTED_PLUGIN_IDENTITIES.get(
                package,
                (f"{package.replace('_', '-')}-kit", "1.0.0"),
            )[0]
        manifest = {
            "$schema": VALIDATOR.PORTABLE_SCHEMA,
            "name": plugin_name,
            "description": "Example plugin.",
            "version": "1.0.0",
            "author": {"name": "Example Team"},
            "license": "MIT",
            "keywords": ["example"],
        }
        self.write(f"{package}/plugin.json", json.dumps(manifest))

        marketplace_path = VALIDATOR.ROOT / ".github" / "plugin" / "marketplace.json"
        if marketplace_path.exists():
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        else:
            marketplace = {
                "name": VALIDATOR.EXPECTED_MARKETPLACE_NAME,
                "owner": {"name": "Example Team"},
                "plugins": [],
            }
        marketplace["plugins"].append({**manifest, "source": package})
        self.write(
            ".github/plugin/marketplace.json",
            json.dumps(marketplace),
        )

    def run_main(self) -> int:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return VALIDATOR.main()

    def test_nested_metadata_is_accepted(self):
        skill_path = self.write(
            "openness_development/skills/example-skill/SKILL.md",
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
            "openness_development/skills/example-skill/SKILL.md",
            "---\n"
            "name: example-skill\n"
            "description: Example description.\n"
            "depends_on: [other-skill]\n"
            "---\n\n"
            "# Example\n",
        )
        errors = []

        VALIDATOR.validate_skills(errors, [], expected_skills_by_plugin=None)

        self.assertTrue(
            any("unsupported skill frontmatter fields: depends_on" in error for error in errors),
            errors,
        )

    def test_links_inside_code_are_ignored(self):
        skill_path = self.write("openness_development/skills/example-skill/SKILL.md", "")
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
        VALIDATOR.validate_skills(errors, [], expected_skills_by_plugin=None)

        self.assertIn("no plugin package directories found", errors)
        self.assertNotEqual(0, self.run_main())

    def test_missing_manifest_is_an_error(self):
        self.write_approved_openness_skills()
        errors = []
        VALIDATOR.validate_manifests(errors)

        self.assertIn(
            f"missing Agent Plugins manifest: "
            f"{Path('openness_development') / 'plugin.json'}",
            errors,
        )
        self.assertNotEqual(0, self.run_main())

    def test_missing_approved_skill_returns_nonzero(self):
        missing = next(
            iter(VALIDATOR.EXPECTED_SKILLS_BY_PLUGIN["openness_development"])
        )
        self.write_approved_openness_skills(missing=missing)
        self.write_manifests()

        self.assertNotEqual(0, self.run_main())

    def test_malformed_manifest_is_an_error(self):
        self.write_approved_openness_skills()
        self.write("openness_development/plugin.json", "{")
        errors = []
        VALIDATOR.validate_manifests(errors)

        self.assertTrue(
            any("invalid JSON" in error for error in errors),
            errors,
        )
        self.assertNotEqual(0, self.run_main())

    def test_broken_link_is_an_error(self):
        self.write_approved_openness_skills()
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
        for name in VALIDATOR.EXPECTED_SKILLS_BY_PLUGIN["openness_development"]:
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
            "openness_development/skills/example-skill/SKILL.md",
            (
                "---\n"
                "description: Example description.\n"
                "metadata:\n"
                f'  {VALIDATOR.DEPENDENCY_METADATA_KEY}: "missing-skill"\n'
                "---\n"
            ),
        )
        errors = []

        VALIDATOR.validate_skills(errors, [], expected_skills_by_plugin=None)

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
        VALIDATOR.validate_skills(errors, [], expected_skills_by_plugin=None)

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
            any("plugin version differs from plugin.json" in error for error in errors),
            errors,
        )

    def test_valid_minimal_repository_passes_without_legacy_manifest(self):
        self.write_skill("example-skill", package="example_plugin")
        self.write_manifests(package="example_plugin")
        errors = []
        warnings = []

        VALIDATOR.validate_skills(
            errors,
            warnings,
            expected_skills_by_plugin=None,
        )
        VALIDATOR.validate_manifests(errors)
        VALIDATOR.validate_documents(errors)

        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_multiple_plugin_packages_are_supported(self):
        self.write_approved_openness_skills()
        self.write_manifests()
        self.write_skill("other-skill", package="other_development")
        self.write_manifests(
            package="other_development",
            plugin_name="other-development-kit",
        )

        self.assertEqual(0, self.run_main())

    def test_every_plugin_package_must_be_listed_in_marketplace(self):
        self.write_approved_openness_skills()
        self.write_manifests()
        self.write_skill("other-skill", package="other_development")
        errors = []

        VALIDATOR.validate_manifests(errors)

        self.assertTrue(
            any("missing marketplace entry for other_development" in error for error in errors),
            errors,
        )


if __name__ == "__main__":
    unittest.main()
