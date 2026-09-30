# Contributing

Contributions that improve the TIA Portal skills are welcome.

Participation in this project is governed by our
[Code of Conduct](CODE_OF_CONDUCT.md).

For questions and bug reports, use
[GitHub Issues](https://github.com/siemens/tia-portal-ai-extensions/issues).

## Make a change

1. Create a branch from `main`.
2. Update the affected skills or documentation.
3. Run the local checks:

   ```shell
   python .github/scripts/validate_skills.py
   python -m unittest discover -s .github/scripts/tests -p "test_*.py"
   ```

4. Open a pull request and describe what changed and how it was verified.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
Examples:

- `feat(skills): add a new Openness skill`
- `fix(blocks): correct the import example`
- `docs: clarify installation`

## Add a skill

- Create `openness_development/skills/<skill-name>/SKILL.md`.
- Use a lowercase, hyphen-separated skill name.
- Add the skill to the `openness_development` entry in
  `EXPECTED_SKILLS_BY_PLUGIN` in
  `.github/scripts/validate_skills.py`.
- Add it to the skill list in `openness_development/README.md`.
- Include only information and examples that may be published.

Do not include credentials, confidential information, internal-only links, or
material that cannot be distributed publicly.

Report confidential or security-sensitive concerns as described in
[SECURITY.md](SECURITY.md).

## Add a plugin

- Create a top-level package directory with a portable `plugin.json`, a
  `README.md`, and a `skills/` directory.
- Add the package to `.github/plugin/marketplace.json`, using the package
  directory as its `source`.
- Add the plugin identity and approved skill names to the corresponding
  mappings in `.github/scripts/validate_skills.py`.
- Run the validation script and regression tests before opening a pull request.
