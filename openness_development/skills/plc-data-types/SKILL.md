---
name: plc-data-types
description: TIA Portal PLC Data Types (UDTs / PlcType) — TypeGroup navigation, recursive search, UDT XML export structure (Section Name="None"), and Member attribute formats. Use when writing or reviewing C# code that accesses, searches, creates, or parses UDTs in PlcSoftware.TypeGroup.
metadata:
  siemens-depends-on: "openness-base, devices-and-hardware"
---

# PLC Data Types (UDTs)

## Overview

PLC Data Types (UDTs) live in `PlcSoftware.TypeGroup` as `PlcType` objects. They are completely separate from blocks (`PlcSoftware.BlockGroup`) and from library types (`GlobalLibrary.TypeFolder`). This skill covers TypeGroup navigation, recursive search, and the XML export structure for UDTs.

## Required Namespaces

```csharp
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Types;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`

---

## 1. TypeGroup Structure

```
PlcSoftware
└── TypeGroup                     ← PlcTypeSystemGroup (root for all UDTs)
	├── Types                     ← PlcTypeComposition
	└── Groups                    ← PlcTypeUserGroupComposition
		└── PlcTypeUserGroup
			├── Types
			└── Groups            ← can nest arbitrarily deep
```

`PlcTypeUserGroup` sub-folders are purely organizational — they are NOT SW-Units.

---

## 2. Finding a UDT

`Types.Find(name)` searches only the current group level. For deep search, recurse into `Groups`:

```csharp
PlcType FindTypeRecursive(PlcTypeGroup group, string name)
{
	var result = group.Types.Find(name);
	if (result != null) return result;
	foreach (var sub in group.Groups)
	{
		result = FindTypeRecursive(sub, name);
		if (result != null) return result;
	}
	return null;
}
```

To search across the **entire PLC** (root and all SW-Units), see [`sw-units`](../sw-units/SKILL.md).

---

## 3. Creating and Navigating Sub-Groups

```csharp
var group = plcSoftware.TypeGroup.Groups.Find("FolderA")
		 ?? plcSoftware.TypeGroup.Groups.Create("FolderA");
```

Group nesting is unlimited. Always use `Find` before `Create` to avoid duplicates.

---

## 4. UDT XML Export — Section Name Rule

When a PLC Data Type (`SW.Types.PlcStruct`) is exported via Openness, its members are **always** inside `<Section Name="None">`.

```xml
<SW.Types.PlcStruct>
  <AttributeList>
	<Interface>
	  <Sections xmlns="http://www.siemens.com/automation/Openness/SW/Interface/v5">
		<Section Name="None">          <!-- ALWAYS "None" for UDTs — never "Static" -->
		  <Member Name="SetPoint"      Datatype="Real" />
		  <Member Name="Enable"        Datatype="Bool" />
		  <Member Name="Config"        Datatype="&quot;MyNamespace.ConfigUDT&quot;" />
		  <Member Name="Buffer"        Datatype="Array[0..9] of Real" />
		</Section>
	  </Sections>
	</Interface>
	<Name>MyUDT</Name>
  </AttributeList>
</SW.Types.PlcStruct>
```

**Critical rule:** Never look for `<Section Name="Static">` when parsing UDT exports — that section name belongs exclusively to Global DBs (`SW.Blocks.GlobalDB`). UDTs always use `"None"`.

---

## 5. Member Attribute Formats

Each `<Member>` element carries:

| Attribute | Format | Example |
|---|---|---|
| Primitive type | Plain type name | `Datatype="Real"`, `Datatype="Bool"`, `Datatype="Int"` |
| UDT reference | XML-escaped quoted name | `Datatype="&quot;MyNamespace.MyUDT&quot;"` |
| Array | Array declaration | `Datatype="Array[0..9] of Real"` |
| Array of UDT | Combined | `Datatype="Array[0..3] of &quot;MyUDT&quot;"` |

When parsing member data types programmatically, unescape `&quot;` → `"` before processing.

---

## Quick Reference

| Goal | API |
|---|---|
| Find UDT by name (one level) | `PlcTypeGroup.Types.Find(name)` |
| Find UDT recursively | Recurse into `group.Groups` manually |
| Create type sub-group | `group.Groups.Find(name) ?? group.Groups.Create(name)` |
| Place UDT from LibraryType | `typeGroup.Types.CreateFrom(udtVersion, UpdatePathsMode.UpdatePathsInTarget)` |
| Place UDT from MasterCopy | `typeGroup.Types.CreateFrom(mc, MasterCopyMode.ThrowIfExists)` |
| UDT XML section name | `<Section Name="None">` — always, never `"Static"` |

## Common Failure Modes

| Symptom | Root Cause | Fix |
|---|---|---|
| UDT not found | Searching only one group level | Recurse into `Groups` |
| No members extracted from XML | Parsing `Section Name="Static"` instead of `"None"` | Look for `Section Name="None"` for UDTs |
| Duplicate type sub-group | `Create` called without `Find` first | Always `Find` before `Create` |

## Related Files

- [`sw-units`](../sw-units/SKILL.md) — PLC-wide UDT search across root and all SW-Unit TypeGroups
- [`global-library`](../global-library/SKILL.md) — placing UDTs from library (MasterCopy or LibraryType path)
- [`blocks`](../blocks/SKILL.md) — blocks live in `BlockGroup`, not `TypeGroup`
