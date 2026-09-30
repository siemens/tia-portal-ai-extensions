---
name: sw-units
description: TIA Portal SW-Unit (PlcUnit) patterns — isolated group hierarchies, PLC-wide search across root and all SW-Units, element creation inside a SW-Unit, Instance DB creation when the source FB lives in a SW-Unit, and placing a SW-Unit from a MasterCopy. Use when writing or reviewing C# code that searches for blocks/types/tag-tables that may be inside a SW-Unit, or creates elements in the correct group context.
metadata:
  siemens-depends-on: "openness-base, devices-and-hardware"
---

# SW-Units (PlcUnit)

## Overview

A Software Unit (`PlcUnit`) is an independent `SoftwareContainer` within the PLC. It exposes its own `BlockGroup`, `TypeGroup`, and `TagTableGroup` that are **completely isolated** from — and invisible to — the root `PlcSoftware` groups. Any search or creation logic that only walks `PlcSoftware.BlockGroup` will silently miss elements that live inside a SW-Unit.

## Required Namespaces

```csharp
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.SW.Types;
using Siemens.Engineering.SW.Tags;
using Siemens.Engineering.SW.Units;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`

---

## 1. SW-Unit Group Isolation

```
PlcSoftware
├── BlockGroup            ← PLC root blocks
├── TypeGroup             ← PLC root UDTs
├── TagTableGroup         ← PLC root tag tables
└── GetService<PlcUnitProvider>()
	└── UnitGroup
		└── PlcUnit: "Unit_1"
			├── BlockGroup    ← SEPARATE — invisible from PlcSoftware.BlockGroup
			├── TypeGroup     ← SEPARATE — invisible from PlcSoftware.TypeGroup
			└── TagTableGroup ← SEPARATE — invisible from PlcSoftware.TagTableGroup
```

Searching `PlcSoftware.BlockGroup` recursively will **never** find blocks inside a SW-Unit, and vice versa.

### Accessing SW-Units

```csharp
var unitProvider = plcSoftware.GetService<PlcUnitProvider>();
if (unitProvider != null)
{
	foreach (PlcUnit unit in unitProvider.UnitGroup.Units)
	{
		// unit.BlockGroup    — blocks inside this SW-Unit
		// unit.TypeGroup     — UDTs inside this SW-Unit
		// unit.TagTableGroup — tag tables inside this SW-Unit
	}
}
```

`PlcUnitProvider` may be `null` if the PLC variant does not support SW-Units (e.g. certain Safety PLC variants). Always guard with a null check.

SW-Units cannot be nested — there is exactly one level of `PlcUnit` under `PlcUnitProvider.UnitGroup.Units`.

---

## 2. PLC-Wide Search (Root + All SW-Units)

When the target group is not known upfront, search both the PLC root and all SW-Unit groups. A single recursive search of `PlcSoftware.BlockGroup` is **not sufficient**.

### Block search

```csharp
PlcBlock FindBlockPlcWide(PlcSoftware plcSw, string name)
{
	// Pass 1: PLC root
	var result = FindBlockRecursive(plcSw.BlockGroup, name);
	if (result != null) return result;

	// Pass 2: all SW-Units
	var unitProvider = plcSw.GetService<PlcUnitProvider>();
	if (unitProvider != null)
		foreach (PlcUnit unit in unitProvider.UnitGroup.Units)
		{
			result = FindBlockRecursive(unit.BlockGroup, name);
			if (result != null) return result;
		}
	return null;
}

PlcBlock FindBlockRecursive(PlcBlockGroup group, string name)
{
	var result = group.Blocks.Find(name);
	if (result != null) return result;
	foreach (var sub in group.Groups)
	{
		result = FindBlockRecursive(sub, name);
		if (result != null) return result;
	}
	return null;
}
```

### Type (UDT) search — same pattern

```csharp
PlcType FindTypePlcWide(PlcSoftware plcSw, string name)
{
	var result = FindTypeRecursive(plcSw.TypeGroup, name);
	if (result != null) return result;
	var unitProvider = plcSw.GetService<PlcUnitProvider>();
	if (unitProvider != null)
		foreach (PlcUnit unit in unitProvider.UnitGroup.Units)
		{
			result = FindTypeRecursive(unit.TypeGroup, name);
			if (result != null) return result;
		}
	return null;
}
```

### Tag table search — same pattern

```csharp
PlcTagTable FindTagTablePlcWide(PlcSoftware plcSw, string name)
{
	var result = FindTagTableRecursive(plcSw.TagTableGroup, name);
	if (result != null) return result;
	var unitProvider = plcSw.GetService<PlcUnitProvider>();
	if (unitProvider != null)
		foreach (PlcUnit unit in unitProvider.UnitGroup.Units)
		{
			result = FindTagTableRecursive(unit.TagTableGroup, name);
			if (result != null) return result;
		}
	return null;
}
```

---

## 3. Creating Elements Inside a SW-Unit

Always use the SW-Unit's own group — never the PLC root group — when the element should live inside the unit:

```csharp
// Blocks
unit.BlockGroup.Blocks.CreateFrom(mc, MasterCopyMode.ThrowIfExists);

// UDTs
unit.TypeGroup.Types.CreateFrom(mc, MasterCopyMode.ThrowIfExists);

// Tag tables
unit.TagTableGroup.TagTables.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
```

Sub-groups within a SW-Unit work identically to sub-groups at PLC root level:

```csharp
var subGroup = unit.BlockGroup.Groups.Find("MySubGroup")
			?? unit.BlockGroup.Groups.Create("MySubGroup");
subGroup.Blocks.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
```

---

## 4. Instance DB Creation When Source FB Is Inside a SW-Unit

`CreateInstanceDB` accepts the source FB name as a string — you must verify the FB exists before calling, and it may be inside a SW-Unit.

```csharp
// Step 1: locate source FB — search current unit first, then PLC root
PlcBlock sourceFb = FindBlockRecursive(unit.BlockGroup, sourceFbName)
				 ?? FindBlockRecursive(plcSoftware.BlockGroup, sourceFbName);

if (sourceFb == null)
	throw new Exception($"Source FB '{sourceFbName}' not found.");

// Step 2: create the IDB in the correct group
// Pass -1 for automatic numbering (throws if auto-numbering is disabled at PLC level)
unit.BlockGroup.Blocks.CreateInstanceDB(idbName, true, -1, sourceFbName);
```

### Automatic numbering

- `-1` = let TIA Portal assign the block number automatically.
- If automatic numbering is **disabled** at the PLC level, passing `-1` throws: `"When automatic numbering is disabled, a valid block number must be assigned."` — always allow the caller to supply an explicit block number as an override.

---

## 5. Placing a SW-Unit from a Library MasterCopy

SW-Units can only be placed from a MasterCopy (no LibraryType equivalent):

```csharp
var unitProvider = plcSoftware.GetService<PlcUnitProvider>()
	?? throw new Exception("PlcUnitProvider not available on this PLC software.");
unitProvider.UnitGroup.Units.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
```

---

## 6. ExternalSourceGroup Isolation per SW-Unit

`ExternalSourceGroup` follows the same isolation rule as `BlockGroup`, `TypeGroup`, and `TagTableGroup`: each SW-Unit has its **own** `ExternalSourceGroup`, completely separate from the PLC root `PlcSoftware.ExternalSourceGroup`.

When importing an SCL source into a SW-Unit, always use **that unit's** `ExternalSourceGroup`. Using `plcSoftware.ExternalSourceGroup` targets the PLC root, not the SW-Unit.

```csharp
// Import SCL source into a SW-Unit — use the unit's own ExternalSourceGroup
var externalSource = unit.ExternalSourceGroup.ExternalSources
    .CreateFromFile(sourceFile.Name, sourceFile.FullName);
externalSource.GenerateBlocksFromSource();
externalSource.Delete();

// Wrong — imports to PLC root, not to the SW-Unit
var externalSource = plcSoftware.ExternalSourceGroup.ExternalSources
    .CreateFromFile(sourceFile.Name, sourceFile.FullName);
```

For `ImportFromDocuments` (SIMATIC SD), supply the SW-Unit's `BlockGroup.Blocks`:

```csharp
// SD import targets the SW-Unit's block group
unit.BlockGroup.Blocks.ImportFromDocuments(dir, name, ImportDocumentOptions.Override);
```

---

## Quick Reference

| Goal | API |
|---|---|
| Access SW-Unit provider | `plcSoftware.GetService<PlcUnitProvider>()` — may return `null` |
| Enumerate SW-Units | `unitProvider.UnitGroup.Units` |
| Find or create SW-Unit | `units.Find(name)` / `units.Create(name)` |
| Place SW-Unit from MasterCopy | `units.CreateFrom(mc, MasterCopyMode.ThrowIfExists)` |
| Create block in SW-Unit | `unit.BlockGroup.Blocks.CreateFrom(mc, ...)` |
| Create UDT in SW-Unit | `unit.TypeGroup.Types.CreateFrom(mc, ...)` |
| Create tag table in SW-Unit | `unit.TagTableGroup.TagTables.CreateFrom(mc, ...)` |
| Import SCL source into SW-Unit | `unit.ExternalSourceGroup.ExternalSources.CreateFromFile(...)` |
| Import SD document into SW-Unit | `unit.BlockGroup.Blocks.ImportFromDocuments(dir, name, options)` |
| PLC-wide block search | Search `plcSw.BlockGroup` then each `unit.BlockGroup` |

## Common Failure Modes

| Symptom | Root Cause | Fix |
|---|---|---|
| Block/type/tag table not found | Searching only PLC root; element is in a SW-Unit | Search both PLC root and all SW-Unit groups |
| SCL source compiled to PLC root instead of SW-Unit | Used `plcSoftware.ExternalSourceGroup` | Use `unit.ExternalSourceGroup` for SW-Unit-targeted imports |
| Element created at PLC root instead of SW-Unit | Using `plcSoftware.BlockGroup` for creation | Use `unit.BlockGroup` / `unit.TypeGroup` / `unit.TagTableGroup` |
| "Valid block number must be assigned" | Auto-numbering disabled, `-1` passed | Accept and pass an explicit block number |
| `PlcUnitProvider` is `null` | PLC does not support SW-Units | Guard with null check before accessing units |
| SW-Unit not found after MasterCopy placement | Wrong name or placement target | Verify name with `units.Find` after `CreateFrom` |

## Related Files

- [`devices-and-hardware`](../devices-and-hardware/SKILL.md) — locating `PlcSoftware` from a device; `PlcUnitProvider` access
- [`global-library`](../global-library/SKILL.md) — MasterCopy placement routing (incl. SW-Unit and TO rules)
- [`plc-data-types`](../plc-data-types/SKILL.md) — UDT TypeGroup structure
- [`blocks`](../blocks/SKILL.md) — block group navigation and import
- [`simatic-sd`](../simatic-sd/SKILL.md) — SD document export/import; use `unit.BlockGroup.Blocks.ImportFromDocuments` for SW-Unit targets
