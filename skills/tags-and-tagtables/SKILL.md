---
name: tags-and-tagtables
description: Tags and tag tables management in TIA Portal. Use when accessing, creating, renaming PLC tags, exporting/importing tag tables to XML, and finding tags by name.
metadata:
  siemens-depends-on: "openness-base, engineering-objects"
---

# Tags and TagTables

## Overview

Tags and TagTables provide the mechanism for defining and managing PLC variables in TIA Portal. A `PlcSoftware` contains a `TagTableGroup` which organizes `PlcTagTable` instances (e.g., default tag tables, HW tags). Each tag table holds a collection of `PlcTag` objects that represent individual variables accessible from blocks. Tags can be accessed by name, edited in-place, exported to XML for bulk modification, and re-imported.

## Required Namespaces

```csharp
using Siemens.Engineering;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Tags;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`

## Common Patterns

### Access TagTable and PlcTag from PlcSoftware

**Description:** Navigate from `PlcSoftware` to its tag tables and individual tags. The `TagTableGroup` exposes all tag tables associated with the PLC software. Tags are accessed via the `Tags` property of a specific tag table.

**Example:**

```csharp
var myTagTable = plcSoftware.TagTableGroup.TagTables.FirstOrDefault(x => x.Name == "DemocaseAppTagTable");
var myTag = myTagTable.Tags.FirstOrDefault();
```

**Key Types and Methods:**
- `PlcSoftware.TagTableGroup` — the root container for all tag tables
- `TagTableCollection` — enumerable collection of tag tables
- `PlcTagTable.Tags` — collection of tags within a tag table

### Edit Tag Name In-Place

**Description:** Modify the name of an existing `PlcTag` directly by setting its `Name` property. This is an in-place mutation on the engineering object.

**Example:**

```csharp
if (myTag != null)
{
    myTag.Name = "NewTagName2";
}
```

**Key Types and Methods:**
- `PlcTag.Name` — settable property for the tag's symbolic name

### Export TagTable to XML and Re-Import

**Description:** Export an entire tag table to XML, modify the XML using standard .NET XML APIs (e.g., `XDocument`), then re-import the modified XML back into the project. Useful for bulk tag transformations or migration scenarios.

**Example:**

```csharp
myTagTable.Export(new FileInfo(tempPath), ExportOptions.WithDefaults);
// ... modify XML with XDocument ...
plcSoftware.TagTableGroup.TagTables.Import(new FileInfo(tempPath), ImportOptions.Override);
```

**Key Types and Methods:**
- `PlcTagTable.Export(FileInfo, ExportOptions)` — writes tag table to XML file
- `TagTableCollection.Import(FileInfo, ImportOptions)` — imports tag table from XML file

### Find Tag by Name via Collection.Find

**Description:** Use the `Find(string)` method on a `PlcTagCollection` to locate a specific tag by its name. This is more efficient than iterating manually and handles name lookup internally.

**Example:**

```csharp
var connectedTag = plcSoftware.TagTableGroup.TagTables
    .First(x => x.Name.ToLower().Contains("default")).Tags.Find("test");
```

**Key Types and Methods:**
- `PlcTagCollection.Find(string)` — returns the tag with the specified name or `null`

### Create and Manage User Constants

**Description:** User constants are named values stored in tag tables, usable in PLC code and array bounds. Use `Find` before `Create` to avoid duplicates.

**Example:**

```csharp
// Find existing constant
var constant = table.UserConstants.Find("MAX_AXES");

// Create if not found
if (constant == null)
    constant = table.UserConstants.Create("MAX_AXES", "Int", "10");

// Update value of an existing constant
constant.Value = "12";
```

**Key Types and Methods:**
- `PlcTagTable.UserConstants` — collection of user constants in the tag table
- `UserConstants.Find(name)` — returns `null` if not found
- `UserConstants.Create(name, dataType, value)` — creates and returns the new constant
- `PlcUserConstant.Value` — settable property for the constant's current value

User constants are referenced in array bounds and PLC code as `"CONST_NAME"` (with quotes).

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `plcSoftware.TagTableGroup.TagTables` | Access all tag tables in the PLC software |
| `PlcTagTable.Tags.FirstOrDefault()` | Get the first tag from a tag table |
| `PlcTag.Name = "..."` | Rename an existing tag in-place |
| `PlcTagTable.Export(path, ExportOptions)` | Export tag table to XML file |
| `TagTableCollection.Import(path, ImportOptions)` | Import tag table from XML file |
| `PlcTagCollection.Find(name)` | Find a tag by its symbolic name |
| `PlcTagTable.UserConstants.Find(name)` | Find a user constant by name |
| `PlcTagTable.UserConstants.Create(name, dataType, value)` | Create a new user constant |
| `PlcUserConstant.Value` | Read or update the constant's value |

## Related Files

- [`blocks`](../blocks/SKILL.md) — blocks reference tags through their interface members
- [`devices-and-hardware`](../devices-and-hardware/SKILL.md) — hardware tags are auto-generated from device configuration

## Exception Handling

- `EngineeringException` may be thrown when exporting/importing tag tables if the file path is invalid or the XML is malformed
- Null checks should be performed after `Find()` calls since they return `null` when the tag is not found
