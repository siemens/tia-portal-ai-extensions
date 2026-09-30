---
name: software-hierarchy
description: PlcSoftware root plus BlockGroup, TypeGroup, TagTableGroup, and ExternalSourceGroup object model. Use when writing or reviewing C# code that navigates or creates PLC software elements beneath a PlcSoftware or SW-Unit context.
metadata:
  siemens-depends-on: "openness-base"
---

# Software Hierarchy (PlcSoftware)

## Overview

Use this as an orientation and routing guide for PLC software scope. It identifies the raw Openness path, the independent hierarchy roots, and the correct import destination. For CRUD details, deep searches, and format-specific behavior, follow the linked specialist skills.

## Required Namespaces

```csharp
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Units;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`

`HW` and `SW` are namespaces, not separate `Siemens.Engineering.HW.dll` or `Siemens.Engineering.SW.dll` assemblies.

---

## Raw Openness path to `PlcSoftware`

In the raw API, start from the CPU `DeviceItem`, obtain its `SoftwareContainer` service, then cast `SoftwareContainer.Software` to `PlcSoftware`:

```csharp
DeviceItem cpu = /* CPU DeviceItem */;
SoftwareContainer container = cpu.GetService<SoftwareContainer>();
PlcSoftware plcSoftware = container?.Software as PlcSoftware;
```

This describes the raw Openness path; framework wrappers may expose a different navigation surface. `SoftwareContainer` is a `DeviceItem` service, not a service on `Device`.

## Hierarchy map

```text
PlcSoftware
├── BlockGroup                root blocks and folders
├── TypeGroup                 root PLC data types and folders
├── TagTableGroup             root tag tables and folders
├── ExternalSourceGroup       root text-source imports
├── TechnologicalObjectGroup  root technology objects
└── GetService<PlcUnitProvider>()
    └── UnitGroup.Units
        └── PlcUnit
            ├── BlockGroup
            ├── TypeGroup
            ├── TagTableGroup
            └── ExternalSourceGroup
```

`PlcUnitProvider` may be `null` on PLC software that does not support SW-Units. Guard it before accessing `UnitGroup`.

## Scope and navigation rules

- `BlockGroup`, `TypeGroup`, and `TagTableGroup` are independent group trees; a folder or element in one is not visible in another.
- User constants belong to a `PlcTagTable.UserConstants` composition reached through `TagTableGroup`; they are not a `PlcSoftware` root group.
- `Find(...)` on a composition is single-level. Use the relevant specialist skill when the target folder is not already known.
- The `PlcSoftware` groups are the PLC root scope. Each `PlcUnit` exposes isolated group trees; root searches and creations do not include SW-Unit content.
- `ExternalSourceGroup` follows the target scope: use the root source group for root imports and the unit's source group for SW-Unit imports.

## Import routing

| Input | Target API | Scope rule |
|---|---|---|
| Block XML | `Blocks.Import(...)` | Use the target root or SW-Unit `BlockGroup`. |
| SCL/text source | `ExternalSourceGroup` | Use the `ExternalSourceGroup` belonging to the target root or SW-Unit scope. |
| SIMATIC SD | `Blocks.ImportFromDocuments(...)` | Use the target root or SW-Unit `BlockGroup`. |

## Route detailed work to the specialist skill

| Need | Detailed skill |
|---|---|
| Blocks, folders, XML import/export, compilation, protection | [`blocks`](../blocks/SKILL.md) |
| PLC data types and UDT XML | [`plc-data-types`](../plc-data-types/SKILL.md) |
| Tag tables, tags, addresses, and user constants | [`tags-and-tagtables`](../tags-and-tagtables/SKILL.md) |
| SW-Unit traversal, isolation, placement, and PLC-wide lookup | [`sw-units`](../sw-units/SKILL.md) |
| SIMATIC SD document import/export | [`simatic-sd`](../simatic-sd/SKILL.md) |
| Technology-object creation and configuration | [`technology-objects`](../technology-objects/SKILL.md) |

## Quick checklist

1. Locate the CPU `DeviceItem`, then its `SoftwareContainer`, then `PlcSoftware`.
2. Decide whether the target is PLC root scope or one specific SW-Unit.
3. Select the matching group tree; do not assume another tree or scope will find the element.
4. Null-check `PlcUnitProvider` before using SW-Units.
5. Route XML, SCL, and SIMATIC SD imports through their distinct APIs and the correct target scope.

## Quick reference

| Goal | API / scope |
|---|---|
| Root blocks | `plcSoftware.BlockGroup` |
| Root UDTs | `plcSoftware.TypeGroup` |
| Root tag tables | `plcSoftware.TagTableGroup` |
| User constants | `plcTagTable.UserConstants` after locating the table through `TagTableGroup` |
| Root text sources | `plcSoftware.ExternalSourceGroup` |
| Root technology objects | `plcSoftware.TechnologicalObjectGroup` |
| SW-Unit provider | `plcSoftware.GetService<PlcUnitProvider>()` |
| SW-Unit import target | The corresponding group or `ExternalSourceGroup` on that `PlcUnit` |
