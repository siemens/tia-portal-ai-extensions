# TIA Portal AI Extensions

[![Validate](https://github.com/siemens/tia-portal-ai-extensions/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/siemens/tia-portal-ai-extensions/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Installable AI plugins with practical guidance for working with Siemens TIA
Portal. Each plugin bundles related Agent Skills and can be installed on its
own from this repository's Copilot CLI marketplace.

The skills provide instructions, code patterns, references, and templates for
AI coding assistants. They are not executable libraries: installing a plugin
does not connect to TIA Portal, change an engineering project, or replace the
official Siemens documentation.

## Available plugins

| Plugin | Focus | Skills | Documentation |
| --- | --- | ---: | --- |
| [TIA Portal Openness Development Kit](openness_development/README.md) | TIA Portal Openness API, STEP 7, Startdrive, DCC, and add-in development | 32 | [Plugin README](openness_development/README.md) |

The plugin README includes the full skill catalog, compatibility information,
prerequisites, and additional details about using the Openness guidance.

## Install with GitHub Copilot CLI

Install the Copilot CLI, then register this marketplace and install a plugin:

```shell
copilot plugin marketplace add siemens/tia-portal-ai-extensions
copilot plugin install tia-portal-openness-development-kit@tia-portal-ai-extensions
```

To browse the marketplace or confirm what's installed:

```shell
copilot plugin marketplace browse tia-portal-ai-extensions
copilot plugin list
copilot skill list
```

In an interactive Copilot CLI session, `/skills list` also shows available
skills. The CLI selects relevant skills based on the task and their
descriptions; you can also ask for a particular skill by name.

### Update or uninstall

Update a plugin after a new version is released:

```shell
copilot plugin update tia-portal-openness-development-kit
```

To remove the plugin and, optionally, the marketplace:

```shell
copilot plugin uninstall tia-portal-openness-development-kit
copilot plugin marketplace remove tia-portal-ai-extensions
```

Uninstall the plugin before removing the marketplace that supplies it.

## Compatibility and prerequisites

- The published plugin uses the portable Agent Plugins 1.0 manifest format
  and the Agent Skills `skills/<name>/SKILL.md` layout.
- GitHub Copilot CLI is the currently verified and supported client. Other
  clients that support these formats may be compatible, but are not verified
  by this project.
- Openness guidance is based on TIA Portal V21. TIA Portal and the Openness
  API require Windows; product packages, SDK assemblies, licenses, Windows
  group membership, and firewall approval may also be required.
- Copilot CLI and Siemens engineering products are installed separately; this
  marketplace provides neither.

See the [Openness plugin documentation](openness_development/README.md) for
the detailed compatibility matrix and the requirements for using TIA Portal
Openness.

## Repository structure

The marketplace catalog is at `.github/plugin/marketplace.json`. Each
installable plugin lives in its own top-level package directory and has its
own portable `plugin.json`, documentation, and skills:

```text
.
├── .github/
│   └── plugin/
│       └── marketplace.json
└── openness_development/
    ├── plugin.json
    ├── README.md
    └── skills/
        └── <skill-name>/
            └── SKILL.md
```

This keeps plugins independently installable. New, separately installable
skill sets belong in a new package directory and a new marketplace entry;
skills that are part of an existing plugin belong directly under that
plugin's `skills/` directory.

## Contributing and validation

Contributions are welcome. The [contribution guide](CONTRIBUTING.md) describes
how to add a skill or plugin and how changes are reviewed.

Run the repository validator and regression tests from the repository root:

```shell
python .github/scripts/validate_skills.py
python -m unittest discover -s .github/scripts/tests -p "test_*.py"
```

## Support, security, and conduct

- For questions, bugs, and improvement suggestions, use
  [GitHub Issues](https://github.com/siemens/tia-portal-ai-extensions/issues).
- For confidential or security-sensitive concerns, follow
  [SECURITY.md](SECURITY.md); do not report vulnerabilities in a public issue.
- Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This repository is licensed under the [MIT License](LICENSE).
