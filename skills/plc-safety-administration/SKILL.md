---
name: plc-safety-administration
description: TIA Portal Openness PLC Safety Administration object model (Siemens.Engineering.Safety). Use when writing or reviewing C# code that configures fail-safe PLCs via SafetyAdministration, SafetySettings, AssignmentOfBlockNumbers, or RuntimeGroup creation and reconciliation.
metadata:
  siemens-depends-on: "openness-base, devices-and-hardware, blocks"
---

# PLC Safety Administration

## Overview

`SafetyAdministration` is the Openness service for configuring fail-safe (F-CPU) PLCs. It exposes safety system version selection, block-number range assignment, and runtime group management. All safety types live in `Siemens.Engineering.Safety`.

> **Note:** This skill covers PLC-level safety administration (`Siemens.Engineering.Safety`). For drive-level safety commissioning (SINAMICS PROFIsafe, STO, etc.) see [`safety-commissioning`](../safety-commissioning/SKILL.md).

## Required Namespaces

```csharp
using Siemens.Engineering.Safety;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`
- `Siemens.Engineering.Safety.dll`

---

## 1. Object Model Overview

```
DeviceItem  (CPU slot — same DeviceItem that exposes SoftwareContainer)
└── GetService<SafetyAdministration>()
	├── Settings : SafetySettings
	│   ├── SafetySystemVersion              ← set via SetSafetySystemVersion()
	│   └── AssignmentOfBlockNumbers
	│       ├── ManagementMode               ← BlockNumbersManagementMode enum
	│       ├── FromDB / ToDB                ← ushort
	│       ├── FromFB / ToFB                ← ushort
	│       └── FromFC / ToFC                ← ushort
	└── RuntimeGroups : RuntimeGroupComposition
		└── RuntimeGroup instances
			├── Name
			├── MainSafetyBlock    (PlcBlock)
			└── MainSafetyBlockIDB (PlcBlock)
```

---

## 2. Locating SafetyAdministration

### Critical rule: service is on DeviceItem, NOT PlcSoftware

```csharp
// CORRECT
var safety = deviceItem.GetService<SafetyAdministration>();

// WRONG — always returns null
var safety = plcSoftware.GetService<SafetyAdministration>();
```

The `DeviceItem` that exposes `SoftwareContainer` is the **same** `DeviceItem` used for `SafetyAdministration`. Find the CPU slot that returns non-null for both:

```csharp
DeviceItem cpuSlot = device.DeviceItems
	.FirstOrDefault(di => di.GetService<SoftwareContainer>() != null
					   && di.GetService<SafetyAdministration>() != null);
```

For deeply nested `DeviceItem` trees, recurse (see [`devices-and-hardware`](../devices-and-hardware/SKILL.md)).

---

## 3. Safety System Version

```csharp
SafetyAdministration sa       = deviceItem.GetService<SafetyAdministration>();
SafetySettings       settings = sa.Settings;

// Get versions supported by this F-CPU
IList<SafetySystemVersion> available = settings.GetApplicableSafetySystemVersions();

// Match by string representation (e.g. "V2.4")
SafetySystemVersion target = available.FirstOrDefault(v => v.ToString() == "V2.4");
if (target != null)
	settings.SetSafetySystemVersion(target);
// If no match, leave the TIA default in place
```

---

## 4. AssignmentOfBlockNumbers

### Setter ordering rule (critical)

Each individual setter (`FromDB`, `ToDB`, etc.) validates `From ≤ To` on write. Setting them out of order causes a range-violation exception from TIA Portal.

**Algorithm — direction-aware ordering:**

```csharp
// Validate before touching setters
if (targetFrom > targetTo) { /* log error, skip */ return; }

AssignmentOfBlockNumbers abn = settings.AssignmentOfBlockNumbers;

// If range moves UP  → write To first, then From
// If range moves DOWN → write From first, then To
if (targetFrom >= abn.FromDB)  // example for DB range; repeat for FB, FC
{
	abn.ToDB   = targetTo;
	abn.FromDB = targetFrom;
}
else
{
	abn.FromDB = targetFrom;
	abn.ToDB   = targetTo;
}
```

Apply the same pattern independently for DB, FB, and FC ranges.

### ManagementMode

```csharp
BlockNumbersManagementMode mode = Enum.TryParse<BlockNumbersManagementMode>(
	assignmentData.ManagementMode, out var parsed)
	? parsed
	: BlockNumbersManagementMode.FixedRange;

abn.ManagementMode = mode;
```

Supported values: `"FixedRange"`, `"FSystemManaged"`.

---

## 5. RuntimeGroup Reconciliation

### Pattern: match-by-name, create-if-missing

```csharp
RuntimeGroupComposition groups = sa.RuntimeGroups;

RuntimeGroup existing = groups.Find(groupName);
if (existing == null)
{
	// Resolve the main safety FB and its IDB from PlcSoftware first
	PlcBlock mainFb  = FindBlockRecursive(plcSoftware.BlockGroup, mainSafetyBlockName);
	PlcBlock mainIdb = FindBlockRecursive(plcSoftware.BlockGroup, mainSafetyBlockIDbName);

	if (mainFb == null || mainIdb == null)
	{
		// Fail — do NOT fall back to TIA defaults
		throw new InvalidOperationException(
			$"Safety main block '{mainSafetyBlockName}' or its IDB '{mainSafetyBlockIDbName}' not found.");
	}

	existing = groups.Create(groupName, mainFb, mainIdb);
}
```

### Ordering constraint

`RuntimeGroup.Create(name, fb, idb)` requires the referenced `PlcBlock` objects to **already exist** in the PLC software. Always ensure the safety main block and its IDB are created before attempting to create or reconcile runtime groups. In the generation pipeline, safety administration must run **after** all software elements have been created.

### Setting attributes on a RuntimeGroup

Call `SetAttribute` directly on the `RuntimeGroup` object:

```csharp
// CORRECT
existing.SetAttribute("AttributePath", value);
```

Avoid patterns that depend on a wrapper parameter object whose `Parent` reference may be null — calling `GetAttribute`/`SetAttribute` through such a wrapper causes a NullReferenceException if the wrapper was not initialized with a live parent object.

---

## 6. Object Quick Reference

| Object | Type | How to Reach |
|---|---|---|
| `SafetyAdministration` | `Siemens.Engineering.Safety` | `deviceItem.GetService<SafetyAdministration>()` |
| `SafetySettings` | `Siemens.Engineering.Safety` | `sa.Settings` |
| `AssignmentOfBlockNumbers` | `Siemens.Engineering.Safety` | `settings.AssignmentOfBlockNumbers` |
| `BlockNumbersManagementMode` | `Siemens.Engineering.Safety` | `abn.ManagementMode` (enum) |
| `RuntimeGroupComposition` | `Siemens.Engineering.Safety` | `sa.RuntimeGroups` |
| `RuntimeGroup` | `Siemens.Engineering.Safety` | `groups.Find(name)` or `groups.Create(name, fb, idb)` |

---

## Common Failure Modes

| Issue | Root Cause | Correct Approach |
|---|---|---|
| `SafetyAdministration` returns `null` | Called on `PlcSoftware`, not `DeviceItem` | Call `deviceItem.GetService<SafetyAdministration>()` |
| Range-validation exception on setter | Set `From` before `To` when range moves up | Use direction-aware setter ordering |
| Runtime group created with wrong blocks | Falling back to TIA defaults when blocks not found | Fail explicitly if block lookup returns `null` |
| NRE when setting attributes on `RuntimeGroup` | Wrapper parameter object's `Parent` is null | Call `runtimeGroup.SetAttribute(path, value)` directly |
| `groups.Create` throws "blocks not found" | Safety blocks not yet placed | Run safety administration **after** all software generation |

## Related Files

- [`devices-and-hardware`](../devices-and-hardware/SKILL.md) — locating the CPU `DeviceItem` and `SoftwareContainer`
- [`blocks`](../blocks/SKILL.md) — finding blocks by name recursively in `PlcSoftware.BlockGroup`
- [`safety-commissioning`](../safety-commissioning/SKILL.md) — drive-level safety commissioning (Startdrive / SINAMICS)
