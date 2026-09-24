---
name: openness-overview
description: Overview and index of all TIA Portal Openness skills in this plugin. Use when unsure which specific Openness skill applies, when asked what Openness skills/capabilities exist, for a general map of what the Openness Development plugin can do, or for meta-questions like "what are the skills for", "which skill should I use for X", "wofür sind die skills da". Not for actual implementation tasks — those should activate the specific skill listed below instead.
---

# Openness Skills Overview

## Overview

This skill answers **discovery/meta questions** about the TIA Portal Openness plugin itself — "what can it do", "which skill covers X", "wofür sind die skills da" — rather than performing an Openness development task. It is intentionally standalone: it must never pull in every other skill's full content just to answer an overview question. Once the right skill is identified, let *that* skill activate normally (or point the user to it, e.g. "use the `blocks` skill for that").

## How to answer

1. Explain that skills are contextual prompt extensions: each one is loaded in full only when its `description` matches the current task; only `name` + `description` are loaded upfront for all skills.
2. List the relevant skill(s) below with their one-line purpose.
3. If the user's underlying request is actually a concrete task (not just "what exists"), say which skill applies and let it take over — don't try to do the task from this overview skill.

## Skill Index

### General / Foundational

| Skill | Use when |
|---|---|
| `openness-overview` | Discovering which Openness skills exist and routing a concrete task to the appropriate specialist skill |
| `openness-base` | Always alongside any other Openness skill — SDK DLL discovery via registry, `.csproj` setup, `TypeIdentifier` requirements, core prerequisites |
| `session-and-project` | Starting/attaching TIA Portal sessions, opening/saving/archiving/closing projects, retrieving from `.zap` |
| `engineering-objects` | Exclusive access, transactions, attribute read/write, `GetService<T>` patterns, hardware catalog search, object tree navigation, `CustomIdentityProvider` |
| `object-tree-walking` | Schema-free tree traversal via `GetServiceInfos`/`GetService`/`GetAttributeInfos`/`GetAttribute`, matching by Name+TypeIdentifier, cycle prevention, COM proxy dedup |
| `performance-and-caching` | App feels slow, deep object chains in loops, deciding whether/what to cache, batch attribute reads/writes |
| `threading-and-concurrency` | Multi-threaded/background Openness apps, MCP-style servers with concurrent calls, cross-thread exceptions |
| `licensing-and-firewall` | App denied access to TIA Portal, `LicenseNotFoundException`, explaining required Openness rights/licenses |
| `change-detection` | Detecting what changed in a project over time, deciding on re-download/re-compile, tracking library type versions |
| `crash-diagnosis` | Diagnosing hard TIA Portal process crashes during Openness API call sequences, breadcrumb-based localization |
| `openness-testing` | Building or running live TIA Portal integration tests, including `net48` bootstrap, firewall-dialog boundaries, and dedicated CI runners |
| `tia-addin-scaffold` | Creating a brand-new Openness project/add-in from scratch (interview-driven) |

### Devices, Hardware & Network

| Skill | Use when |
|---|---|
| `devices-and-hardware` | Creating devices, finding CPUs, PROFINET subnets, I/O systems, and network interfaces |
| `hardware-and-modules` | Plugging hardware, changing module types, hardware catalog search, motor/encoder projecting, master copies (drives) |
| `networks-and-drivecliq` | Connecting/disconnecting DriveCliq ports, PROFINET interfaces, discovering I/O system topology |
| `online-and-download` | Connecting to CPUs via `OnlineProvider`, downloading PLC software, connection modes, passwords |

### PLC Program

| Skill | Use when |
|---|---|
| `blocks` | Importing/compiling/exporting/protecting PLC blocks, InstanceDB/GlobalDB interface members, cross-references |
| `software-hierarchy` | Orienting within `PlcSoftware` root and SW-Unit group scopes, and routing imports to the correct specialist API |
| `tags-and-tagtables` | Creating/renaming PLC tags, exporting/importing tag tables as XML |
| `plc-data-types` | UDT/`PlcType` navigation and search, UDT XML export structure, member attribute formats |
| `sw-units` | SW-Unit isolated group hierarchies, PLC-wide search across root and SW-Units, element creation inside SW-Units |
| `simatic-sd` | SIMATIC SD block document format (.s7dcl/.s7res), export/import, network insertion, LAD/FBD/SCL detection |
| `plc-safety-administration` | Fail-safe PLC config via `SafetyAdministration`, `AssignmentOfBlockNumbers`, `RuntimeGroup` |
| `technology-objects` | Creating/finding/configuring Technology Objects (axes) for motion control |
| `global-library` | GlobalLibrary traversal, MasterCopy/type placement, library file (.zap/.zal) handling, post-placement rename |
| `libraries-and-alarms` | Global libraries, master copies, alarm text lists, safety administration, runtime groups, unit providers |
| `security` | UMAC custom roles, project users, device function rights, master passwords, CPU protection/access level |

### Drives (SINAMICS / Startdrive)

| Skill | Use when |
|---|---|
| `drive-objects` | Locating DriveObjects, telegrams, writing drive parameters, Double-MoMo drives, refreshing drive state |
| `parameters` | Reading/writing drive parameters, BiCo wiring, parameter access by index/name, parameter bit manipulation |
| `telegrams` | Main/safety telegram configuration, changing telegram numbers, resizing telegram I/O, PROFIsafe telegrams |
| `safety-commissioning` | PROFIsafe functions (STO/SImO), safety checksums, safety axis type, acceptance tests |
| `drive-control-charts` | Creating/importing/exporting DCC charts, blocks, pins, parameters, graphical drive functions |

## Notes

- Descriptions above are summaries; always defer to the linked skill's own `description` frontmatter and `SKILL.md` content as the source of truth — this index is a map, not a replacement.
- When a new Openness skill is added to the plugin, add it to the relevant table above and to the [plugin README](../../README.md).
