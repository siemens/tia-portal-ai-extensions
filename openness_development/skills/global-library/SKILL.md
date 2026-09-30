---
name: global-library
description: TIA Portal GlobalLibrary object model — traversal, element placement, type classification, MasterCopy routing, library file handling (.zap/.zal), and post-placement rename. Use when writing or reviewing C# code that opens a GlobalLibrary, traverses TypeFolder or MasterCopyFolder, places library elements into PLCs, classifies LibraryTypeVersion subclasses, or renames placed elements.
metadata:
  siemens-depends-on: "openness-base, devices-and-hardware, engineering-objects"
---

# Global Library

## Overview

A `GlobalLibrary` exposes reusable engineering content through two independent root containers: a versioned `TypeFolder` (FB, FC, OB, UDT) and an unversioned `MasterCopyFolder` (any element type, including DB, TagTable, SW-Unit). Placement, traversal, and type-classification rules differ between these containers.

## Required Namespaces

```csharp
using Siemens.Engineering;
using Siemens.Engineering.Library;
using Siemens.Engineering.Library.MasterCopies;
using Siemens.Engineering.Library.Types;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.SW.Types;
using Siemens.Engineering.SW.Units;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`

---

## 1. Top-Level Shape

A `GlobalLibrary` has exactly two independent root containers:

| Container | API Property | Purpose |
|---|---|---|
| `TypeFolder` | `GlobalLibrary.TypeFolder` | Versioned Library Types (FB, FC, OB, UDT) |
| `MasterCopyFolder` | `GlobalLibrary.MasterCopyFolder` | Unversioned snapshots (any element, including DB, TagTable, SW-Unit) |

These containers are completely separate in API, hierarchy, and semantics.

---

## 2. Opening a Library — .zap vs .zal

Global libraries come in two file formats. The extension suffix is the TIA Portal version number (e.g. `.zap21`, `.zal21`).

| Extension | Meaning | How to open |
|---|---|---|
| `.zapXX` | Unarchived (unpacked) library — ready to use | `portal.GlobalLibraries.OpenWithUpgrade(new FileInfo(path))` |
| `.zalXX` | Archived (packed) library — must be dearchived first | `portal.GlobalLibraries.Retrieve(new FileInfo(zalPath), new DirectoryInfo(tempDir), OpenMode.ReadOnly)` |

**Rules:**

1. **Always use `OpenWithUpgrade`** (not `Open`) for `.zap` files — it silently upgrades the library format if created by an older TIA Portal version.
2. **`.zal` files must be dearchived** via `GlobalLibraries.Retrieve`. The method extracts the library into the target directory and returns it already opened — no additional `Open` call is needed.
3. **Check for an already-open library first** (by comparing `GlobalLibrary.Path.FullName`) before calling any open method to avoid opening the same library twice.

```csharp
private GlobalLibrary OpenLibrary(TiaPortal portal, string absoluteFilePath)
{
	// Deduplication check
	var existing = portal.GlobalLibraries
		.OfType<GlobalLibrary>()
		.FirstOrDefault(l => string.Equals(l.Path.FullName, absoluteFilePath,
			StringComparison.OrdinalIgnoreCase));
	if (existing != null) return existing;

	var fileInfo = new FileInfo(absoluteFilePath);
	if (fileInfo.Extension.StartsWith(".zal", StringComparison.OrdinalIgnoreCase))
	{
		var tempDir = new DirectoryInfo(Path.Combine(
			Path.GetTempPath(), "Libraries",
			Path.GetFileNameWithoutExtension(absoluteFilePath)));
		if (!tempDir.Exists) tempDir.Create();
		return portal.GlobalLibraries.Retrieve(fileInfo, tempDir, OpenMode.ReadOnly) as GlobalLibrary;
	}

	return portal.GlobalLibraries.OpenWithUpgrade(fileInfo) as GlobalLibrary;
}
```

---

## 3. TypeFolder Traversal

`TypeFolder` is a `LibraryTypeSystemFolder`. Its `Folders` property returns `LibraryTypeUserFolder` sub-folders.

**Critical traversal rule:** The method parameter that receives a folder must be typed as the **base class `LibraryTypeFolder`**, not the derived `LibraryTypeUserFolder`. The Openness API shadows the `Folders` property on the derived type; using the base-class compile-time type ensures the correct property implementation is called.

**Enumeration rule:** `folder.Types` on any `LibraryTypeFolder` returns **only direct children** — the API does NOT enumerate recursively. Full traversal requires manual recursion.

Sub-folders in `TypeFolder` are purely organizational — they do NOT represent SW-Units.

```csharp
void TraverseTypeFolder(LibraryTypeFolder folder)
{
	foreach (var type in folder.Types)
	{
		var latest = type.Versions
			.OfType<LibraryTypeVersion>()
			.OrderBy(v => v.VersionNumber)
			.LastOrDefault();
		// process latest version...
	}
	foreach (LibraryTypeUserFolder sub in folder.Folders)
		TraverseTypeFolder(sub);   // parameter typed as base LibraryTypeFolder
}
```

---

## 4. LibraryTypeVersion Subclasses

For PLC software (`Siemens.Engineering.SW`), exactly two relevant `LibraryTypeVersion` subclasses exist:

| Subclass | Namespace | Creates in PLC |
|---|---|---|
| `PlcTypeLibraryTypeVersion` | `Siemens.Engineering.SW.Types` | PLC Data Type (UDT) |
| `CodeBlockLibraryTypeVersion` | `Siemens.Engineering.SW.Blocks` | Code Block (FB, FC, OB only) |

**What CANNOT be a Library Type:**
- `DataBlock` (GlobalDB, InstanceDB, ArrayDB) — no `LibraryTypeVersion` subclass
- `PlcTagTable` — no `PlcTagTableLibraryTypeVersion` exists
- `PlcUnit` (SW-Unit) — SW-Units can only be stored as Master Copies

The `PlcBlock` hierarchy splits into `CodeBlock` (FB/FC/OB — has `LibraryTypeVersion`) and `DataBlock` (DB — no `LibraryTypeVersion`). Never assume a DB can be a Library Type.

---

## 5. LibraryType vs. PlcType — Naming Distinction

1. **`LibraryType`** (in `GlobalLibrary.TypeFolder`) = a versioned wrapper for ANY reusable library artifact. "Type" means "library type" (versioned artifact), NOT "PLC Data Type." A `LibraryType` can represent a UDT OR a code block.
2. **`PlcType`** (in `PlcSoftware.TypeGroup`) = a PLC Data Type (UDT) living in the PLC program.
3. `LibraryType` ≠ `PlcType`. Corresponding subclasses: `PlcTypeLibraryType` (→ UDT), `CodeBlockLibraryType` (→ FB/FC/OB).

---

## 6. Placement — TypeFolder Path (versioned)

```csharp
var latest = libType.Versions
	.OfType<LibraryTypeVersion>()
	.OrderBy(v => v.VersionNumber)
	.LastOrDefault();

switch (latest)
{
	case PlcTypeLibraryTypeVersion udtVersion:
		typeGroup.Types.CreateFrom(udtVersion, UpdatePathsMode.UpdatePathsInTarget);
		break;
	case CodeBlockLibraryTypeVersion blockVersion:
		blockGroup.Blocks.CreateFrom(blockVersion, UpdatePathsMode.UpdatePathsInTarget);
		break;
}
```

### Bulk-update before individual placement

Call `GlobalLibrary.UpdateProject` first to update already-present elements in one API call. Wrap in try/catch — it may throw for version reasons but should not stop placement:

```csharp
try
{
	lib.UpdateProject(typeSelections, new List<IUpdateProjectScope> { plcSoftware });
}
catch (Exception ex)
{
	// best-effort — continue with CreateFrom
}
```

### Processing order (UDTs before code blocks)

Code blocks may reference UDTs. Always sort so UDTs (`PlcTypeLibraryTypeVersion`) are placed before code blocks:

```csharp
var sorted = types.OrderBy(t => t is PlcTypeLibraryTypeVersion ? 0 : 1).ToList();
```

---

## 7. Placement — MasterCopyFolder Path (unversioned)

Use `MasterCopy.ContentDescriptions` to determine the element type before routing:

```csharp
var raw = mc.ContentDescriptions.FirstOrDefault()?.ContentType?.ToString() ?? "";
// Strip namespace prefix: "Siemens.Engineering.SW.Blocks.FB" -> "FB"
var contentType = raw.Contains(".")
	? raw.Substring(raw.LastIndexOf('.') + 1)
	: raw;

switch (contentType)
{
	case "FB": case "FC": case "OB":
	case "GlobalDB": case "InstanceDB": case "ArrayDB":
		blockGroup.Blocks.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
		break;
	case "PlcType":
		typeGroup.Types.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
		break;
	case "PlcTagTable":
		tagTableGroup.TagTables.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
		break;
	case "PlcUnit":
		unitProvider.UnitGroup.Units.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
		break;
	case "TechnologicalInstanceDB":
		// TOs always live at PLC root — SW-Units have no TechnologicalObjectGroup
		rootPlcSoftware.TechnologicalObjectGroup.TechnologicalObjects
			.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
		break;
}
```

**Technology Object routing rule:** TOs always live at the PLC root. Even when placing all other elements into a SW-Unit, route `TechnologicalInstanceDB` content to `rootPlcSoftware.TechnologicalObjectGroup`. SW-Units have no `TechnologicalObjectGroup`.

---

## 8. Folder Navigation — Group Path Replication

To mirror a library folder hierarchy inside the PLC, traverse each path segment using `Groups.Find` / `Groups.Create`:

```csharp
PlcBlockGroup GetOrCreateBlockGroup(PlcBlockGroup root, IEnumerable<string> segments)
{
	var current = root;
	foreach (var segment in segments)
		current = current.Groups.Find(segment) ?? current.Groups.Create(segment);
	return current;
}
```

---

## 9. Hardware Device / Module Placement from a Library

Hardware elements (PLC stations, drive units, IO devices, modules) can also be stored as Master Copies in a Global Library and placed into the TIA Portal hardware configuration.

### GlobalLib:// Reference Format

Library-sourced hardware references use a `GlobalLib://` URI scheme:

```
GlobalLib://LibraryFileName/Master copies/Folder1/Folder2/ElementName
```

- `LibraryFileName` — matched against `Path.GetFileNameWithoutExtension` of each open library's file path. A robust matcher also strips any `_V<nn>` version suffix that TIA Portal appends on library upgrade (regex `_[Vv]\d+$`).
- `"Master copies"` — fixed second segment; skip it during folder resolution.
- Remaining intermediate segments form the `MasterCopyFolder` sub-path; the last segment is the element name.

### Placing a Device (station-level)

Resolve the `MasterCopy` from `GlobalLibrary.MasterCopyFolder` by walking the parsed folder path, then call `CreateFrom` on the destination `DeviceComposition`:

```csharp
// Resolve library and walk folder path to find the MasterCopy
MasterCopy mc = ResolveMasterCopy(library, folderSegments, elementName);

// Place the hardware device
Device device = destinationDeviceComposition.CreateFrom(mc);
device.SetAttribute("Name", desiredName);   // rename after placement
```

### Placing a Sub-Element (module on a rack slot)

For modules placed under a parent device item, resolve the same way and create under the parent `DeviceItem`:

```csharp
DeviceItem module = parentDeviceItem.DeviceItems.CreateFrom(mc);
module.SetAttribute("Name", desiredName);
```

### Library Filename Resolution

To map a `LibraryFileName` fragment to an actual open `GlobalLibrary`:

```csharp
GlobalLibrary ResolveLibraryByFilename(IEnumerable<GlobalLibrary> openLibraries, string libFileName)
{
    // Normalize: strip _V<digits> suffix that TIA Portal adds on upgrade
    string Normalize(string s) => Regex.Replace(s, @"_[Vv]\d+$", string.Empty);
    string target = Normalize(libFileName);

    return openLibraries.FirstOrDefault(lib =>
        string.Equals(
            Normalize(Path.GetFileNameWithoutExtension(lib.Path.FullName)),
            target,
            StringComparison.OrdinalIgnoreCase));
}
```

---

## 10. Renaming a Placed Element

The Openness API always creates the element using its library-side name. To use a different name in the PLC, rename after creation via `SetAttribute`:

```csharp
var created = blockGroup.Blocks.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
created.SetAttribute("Name", targetName);
```

### Idempotent three-step pattern

**Step 1 — Compute effective name:**
```csharp
var effectiveName = !string.IsNullOrEmpty(targetName) ? targetName : libraryElementName;
```

**Step 2 — Pre-delete by both names** (a previous run may have left either):
```csharp
blockGroup.Blocks.Find(libraryElementName)?.Delete();
blockGroup.Blocks.Find(effectiveName)?.Delete();
```

**Step 3 — Create, then rename:**
```csharp
var created = blockGroup.Blocks.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
if (!string.Equals(targetName, libraryElementName, StringComparison.Ordinal))
	created.SetAttribute("Name", targetName);
```

Apply the same rename logic to both MasterCopy and LibraryType placement paths — asymmetric implementations are a common source of bugs.

---

## 11. Container Lookup Order — Version-Driven Policy

| Caller specifies version? | Search first | Fallback |
|---|---|---|
| Yes (`"newest"`, `"1.2.0"`, …) | `TypeFolder` | `MasterCopyFolder` |
| No / `"default"` | `MasterCopyFolder` | `TypeFolder` |
| Element is a TagTable or SW-Unit | `MasterCopyFolder` only | (no LibraryType equivalent) |

---

## 12. Matching PLC Elements Back to Their Library Type

When blocks from a library have suffixed names in the library (e.g. `"ClassFB_6"`) but are placed in the PLC under the unsuffixed name (`"ClassFB"`), name-based search alone is unreliable.

**Correct approach:** Use `GetService<LibraryTypeInstanceInfo>()` on any `PlcBlock` or `PlcType`:

```csharp
var instanceInfo = block.GetService<LibraryTypeInstanceInfo>();
var parentType = instanceInfo?.LibraryTypeVersion?.Parent as LibraryType;
if (parentType != null &&
	string.Equals(parentType.Name, libraryTypeName, StringComparison.OrdinalIgnoreCase))
	return block; // confirmed match
```

This works for **Library Type instances only**. MasterCopy-placed elements return `null` — fall back to name search in that case.

---

## 13. Tag Table Placement Notes

Tag tables must target the **correct `PlcTagTableGroup`** — either the PLC root or a SW-Unit's isolated group. Never hardcode `PlcSoftware.TagTableGroup` when the target is a SW-Unit.

When a caller supplies additional inline tags/constants on top of a library-placed tag table, apply them after placement:

1. Place master copy → table exists with library-defined content
2. `Find(tableName)` on the target group to get a handle to the placed table
3. Loop through additional tags: `plcTable.Tags.Create(name, dataType, address)`
4. Loop through additional constants: `plcTable.UserConstants.Create(name, dataType, value)`

**Tag name uniqueness:** Tag names are globally unique per PLC (across ALL tag tables). Attempting to create a tag with a name that already exists in any other table throws `"An attempt was made to create an object that already exists."` Include the table name in error messages for diagnostics.

**Resilient attribute setting:** Some tag attributes (e.g. `AccessibleFromHMI`) are not supported on all tag types. Wrap `SetAttribute` in try/catch and log + continue on failure.

---

## Quick Reference

| Goal | API |
|---|---|
| Open `.zap` library | `portal.GlobalLibraries.OpenWithUpgrade(fileInfo)` |
| Open `.zal` library | `portal.GlobalLibraries.Retrieve(fileInfo, tempDir, OpenMode.ReadOnly)` |
| Enumerate library type folders | `GlobalLibrary.TypeFolder.Folders` |
| Enumerate types in folder (direct only) | `LibraryTypeFolder.Types` |
| Get latest version | `.Versions.OfType<LibraryTypeVersion>().OrderBy(v => v.VersionNumber).LastOrDefault()` |
| Bulk-update project from library | `GlobalLibrary.UpdateProject(selections, scopes)` |
| Place UDT LibraryType | `typeGroup.Types.CreateFrom(udtVersion, UpdatePathsMode.UpdatePathsInTarget)` |
| Place code-block LibraryType | `blockGroup.Blocks.CreateFrom(blockVersion, UpdatePathsMode.UpdatePathsInTarget)` |
| Place block MasterCopy | `blockGroup.Blocks.CreateFrom(mc, MasterCopyMode.ThrowIfExists)` |
| Place UDT MasterCopy | `typeGroup.Types.CreateFrom(mc, MasterCopyMode.ThrowIfExists)` |
| Place tag-table MasterCopy | `tagTableGroup.TagTables.CreateFrom(mc, MasterCopyMode.ThrowIfExists)` |
| Place SW-Unit MasterCopy | `unitProvider.UnitGroup.Units.CreateFrom(mc, MasterCopyMode.ThrowIfExists)` |
| Place TO MasterCopy | `rootPlcSoftware.TechnologicalObjectGroup.TechnologicalObjects.CreateFrom(mc, ...)` |
| Rename after placement | `created.SetAttribute("Name", targetName)` |
| Verify library origin | `block.GetService<LibraryTypeInstanceInfo>()` |
| Place hardware device from MasterCopy | `deviceComposition.CreateFrom(mc)` then `SetAttribute("Name", name)` |
| Place hardware module from MasterCopy | `parentDeviceItem.DeviceItems.CreateFrom(mc)` then `SetAttribute("Name", name)` |
| Resolve library by `GlobalLib://` filename | Strip `_V<nn>` suffix; match `Path.GetFileNameWithoutExtension` case-insensitively |

## MasterCopyMode vs UpdatePathsMode — Two Different Enums

These enums are used in different placement APIs and must not be confused:

| Context | Enum | Typical Value |
|---|---|---|
| MasterCopy placement (`blockGroup.Blocks.CreateFrom`, `typeGroup.Types.CreateFrom`, etc.) | `MasterCopyMode` | `ThrowIfExists` or `Replace` |
| LibraryType placement (`CreateFrom` on `PlcBlockComposition` / `PlcTypeComposition`) | `UpdatePathsMode` | `UpdatePathsInTarget` or `KeepExistingPathsInTarget` |

`LibraryType.CreateFrom` takes no `MasterCopyMode` — it always creates a new instance. `MasterCopy.CreateFrom` takes `MasterCopyMode`. Passing the wrong enum type causes a compile error; using the wrong concept causes runtime failures.

---

## `.zal` Path Cache Note

For `.zal` (archived) libraries, the path used to open the library (`absoluteFilePath`) is **different** from the library's runtime `Path.FullName` after `Retrieve` (which points to the extracted temp folder). A deduplication check that scans `portal.GlobalLibraries` by runtime `Path.FullName` cannot match the original `.zal` path.

If you maintain an open-library cache, key it on the **original request path** (not the runtime path) to correctly detect already-opened `.zal` libraries:

```csharp
// Cache keyed on the original file path (before extraction)
if (_pathCache.TryGetValue(absoluteFilePath, out var cached))
    return cached;

// ... open / retrieve ...
_pathCache[absoluteFilePath] = openedLibrary;
```

---

## Common Failure Modes

| Symptom | Root Cause | Fix |
|---|---|---|
| `CreateFrom` throws "already exists" on re-run | Pre-delete only by library name | Also pre-delete by `targetName` |
| Versioned element not renamed, unversioned is | Asymmetric placement helpers | Add rename logic to LibraryType path |
| Tag table / SW-Unit not found in TypeFolder | These types have no LibraryType equivalent | Route to MasterCopyFolder unconditionally |
| Library opens twice | No deduplication check before `Open`/`OpenWithUpgrade` | Check `portal.GlobalLibraries` by `Path.FullName` first |
| `.zal` library opens twice | Cache keyed on runtime `Path.FullName`; `.zal` runtime path differs from original `.zal` path | Key cache on the original request path, not the runtime path |
| `.zal` open fails | Called `OpenWithUpgrade` on archived file | Use `GlobalLibraries.Retrieve` for `.zal` |
| UDT placed after block that references it | No sort before batch placement | Sort: UDTs (`PlcTypeLibraryTypeVersion`) before code blocks |
| TO placed in wrong group | Routed to `blockGroup.Blocks.CreateFrom` | Use `TechnologicalObjectGroup.TechnologicalObjects.CreateFrom` |

## Related Files

- [`devices-and-hardware`](../devices-and-hardware/SKILL.md) — locating `SoftwareContainer` / `PlcSoftware` from a device
- [`sw-units`](../sw-units/SKILL.md) — SW-Unit group isolation and PLC-wide search
- [`plc-data-types`](../plc-data-types/SKILL.md) — UDT / PlcType group structure
- [`technology-objects`](../technology-objects/SKILL.md) — creating TOs from scratch
