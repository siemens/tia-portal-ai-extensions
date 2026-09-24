# TIA Portal AI Extensions

A growing collection of AI extensions that work with Siemens TIA Portal.

This is a help set for AI coding clients, not an executable library or
automation service. The first release provides the
`tia-portal-openness-development-kit` plugin with skills focused on TIA Portal
Openness. Future releases can add further TIA Portal skill sets that are not
limited to Openness.

## Install with GitHub Copilot CLI

The supported installation path uses the marketplace catalog in this repository.

1. Register the marketplace:

   ```shell
   copilot plugin marketplace add siemens/tia-portal-ai-extensions
   ```

2. Install the plugin:

   ```shell
   copilot plugin install tia-portal-openness-development-kit@tia-portal-ai-extensions
   ```

3. Verify the installation:

   ```shell
   copilot plugin list
   ```

   In an interactive Copilot CLI session, run `/skills list` and confirm that
   the plugin's skills are available.

### Update

```shell
copilot plugin update tia-portal-openness-development-kit
```

### Uninstall

```shell
copilot plugin uninstall tia-portal-openness-development-kit
copilot plugin marketplace remove tia-portal-ai-extensions
```

Uninstall the plugin before removing its marketplace. Copilot CLI refuses to
remove a marketplace that still supplies installed plugins unless forced.

Direct installation from a local path or repository may still be useful during
development, but Copilot CLI 1.0.86 marks direct plugin installs as deprecated.
The marketplace flow above is the release installation path.

## Compatibility and prerequisites

| Component | Status |
| --- | --- |
| GitHub Copilot CLI | Installation and discovery of all 32 skills verified with version 1.0.86 |
| Agent Plugins | Root manifest follows Agent Plugins 1.0 |
| Agent Skills | Skills use the standard `skills/<name>/SKILL.md` layout |
| TIA Portal | Content and SDK paths are based on TIA Portal V21; other versions are not verified |
| Operating system | Windows is required for TIA Portal and the Openness API |

This plugin is developed against the official Agent Skills specification and
Agent Plugins 1.0. It is tested and supported with GitHub Copilot CLI. Other
compatible AI clients may be able to use the bundled skills, but they have not
yet been verified and are not currently part of the supported client matrix.

Installing the plugin does not install TIA Portal, an Openness SDK, or any
Siemens product license. To apply the current Openness guidance with TIA Portal,
you need:

- TIA Portal V21 with the product packages used by your application;
- the matching assemblies under
  `$(TiaPortalLocation)\PublicAPI\V21\net48\`;
- the licenses required by those TIA Portal products and options;
- membership in the local Windows group `Siemens TIA Openness`; and
- approval of the application in the TIA Portal Openness firewall.

There is no separate Openness product license, but the underlying products and
options can require licenses. A GitHub Copilot entitlement may also be required
to use Copilot CLI.

## How it works

Ask Copilot CLI for help with a concrete TIA Portal Openness task. It selects
relevant installed skills from their descriptions; you can also inspect the
available skills with `/skills list`.

The plugin supplies Markdown guidance, code patterns, references, and project
templates. It does not itself connect to TIA Portal or execute Openness
operations.

Examples are based on the TIA Portal V21 API. Individual skills identify
empirical findings or operations that still require live verification.

## Included skills

### Foundations and cross-cutting guidance

| Skill | Description |
| --- | --- |
| [`openness-base`](skills/openness-base/SKILL.md) | SDK discovery, assembly references, API versioning, type identifiers, and core prerequisites |
| [`licensing-and-firewall`](skills/licensing-and-firewall/SKILL.md) | Product licensing, Windows-group access, and Openness firewall authorization |
| [`change-detection`](skills/change-detection/SKILL.md) | Project timestamps, fingerprints, PLC checksums, and Safety signatures |
| [`performance-and-caching`](skills/performance-and-caching/SKILL.md) | IPC-aware navigation, batching, caching, reference limits, and bulk-edit performance |
| [`threading-and-concurrency`](skills/threading-and-concurrency/SKILL.md) | Apartment state, thread affinity, serialization, and safe concurrent request handling |

### General

| Skill | Description |
| --- | --- |
| [`session-and-project`](skills/session-and-project/SKILL.md) | TIA Portal session lifecycle and project open, save, archive, and close operations |
| [`engineering-objects`](skills/engineering-objects/SKILL.md) | Exclusive access, transactions, services, attributes, object navigation, and identity |

### STEP 7

| Skill | Description |
| --- | --- |
| [`tags-and-tagtables`](skills/tags-and-tagtables/SKILL.md) | PLC tag and tag-table operations, XML import/export, and user constants |
| [`blocks`](skills/blocks/SKILL.md) | Program and data blocks, import/export, compilation, protection, and cross-references |
| [`devices-and-hardware`](skills/devices-and-hardware/SKILL.md) | Device creation, CPU discovery, software containers, networks, and transfer areas |
| [`online-and-download`](skills/online-and-download/SKILL.md) | Online connections and software download |
| [`security`](skills/security/SKILL.md) | UMAC roles, users, device-function rights, and PLC protection |
| [`libraries-and-alarms`](skills/libraries-and-alarms/SKILL.md) | Global libraries, master copies, alarm text lists, Safety administration, and units |
| [`technology-objects`](skills/technology-objects/SKILL.md) | Technology-object creation, discovery, and parameterization |
| [`global-library`](skills/global-library/SKILL.md) | Global-library traversal, type classification, placement, and rename patterns |
| [`sw-units`](skills/sw-units/SKILL.md) | PLC-wide discovery and creation across root and software-unit scopes |
| [`software-hierarchy`](skills/software-hierarchy/SKILL.md) | PLC software hierarchy and routing through groups and software units |
| [`openness-testing`](skills/openness-testing/SKILL.md) | Live Openness integration-test architecture and runner prerequisites |
| [`plc-data-types`](skills/plc-data-types/SKILL.md) | PLC data types, recursive search, and UDT XML structure |
| [`plc-safety-administration`](skills/plc-safety-administration/SKILL.md) | Fail-safe PLC settings, block-number assignment, and runtime groups |
| [`simatic-sd`](skills/simatic-sd/SKILL.md) | SIMATIC SD documents, V21 import/export, parsing, and network insertion |
| [`crash-diagnosis`](skills/crash-diagnosis/SKILL.md) | Hard-crash localization and safer object-tree inspection |
| [`object-tree-walking`](skills/object-tree-walking/SKILL.md) | Schema-free service, attribute, and composition traversal |

### Startdrive

| Skill | Description |
| --- | --- |
| [`drive-objects`](skills/drive-objects/SKILL.md) | Drive-object access, activation, parameters, hardware projection, and online operations |
| [`hardware-and-modules`](skills/hardware-and-modules/SKILL.md) | Motors, encoders, hardware catalog search, insertion, and type changes |
| [`parameters`](skills/parameters/SKILL.md) | Drive parameters, indexed values, bits, and BiCo wiring |
| [`telegrams`](skills/telegrams/SKILL.md) | Main, safety, additional, and supplementary telegram configuration |
| [`networks-and-drivecliq`](skills/networks-and-drivecliq/SKILL.md) | PROFINET and DriveCliq port connections |
| [`safety-commissioning`](skills/safety-commissioning/SKILL.md) | SINAMICS safety functions, checksums, and acceptance tests |

### DCC

| Skill | Description |
| --- | --- |
| [`drive-control-charts`](skills/drive-control-charts/SKILL.md) | DCC chart import/export, blocks, pins, and parameter interconnection |

### Add-in development

| Skill | Description |
| --- | --- |
| [`tia-addin-scaffold`](skills/tia-addin-scaffold/SKILL.md) | Guided creation of packaged add-ins and standalone Openness applications |

### Discovery

| Skill | Description |
| --- | --- |
| [`openness-overview`](skills/openness-overview/SKILL.md) | Overview and routing help for all skills in this plugin |

## Support

Use [GitHub Issues](https://github.com/siemens/tia-portal-ai-extensions/issues)
for questions, bugs, and improvement suggestions.

For confidential or security-sensitive concerns, follow
[SECURITY.md](SECURITY.md) instead of opening a public issue.

Community participation is governed by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

Copyright (c) 2026 Siemens AG. This project is licensed under the
[MIT License](LICENSE).
