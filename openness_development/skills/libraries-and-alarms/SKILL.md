---
name: libraries-and-alarms
description: Libraries and alarms in TIA Portal. Use when creating global libraries, managing master copies, accessing alarm text lists, safety administration, runtime groups, and unit providers.
metadata:
  siemens-depends-on: "openness-base, engineering-objects, blocks"
---

# Libraries and Alarms

## Overview

Libraries provide reusable engineering content (blocks, tags, etc.) across projects. The `UserGlobalLibrary` is the primary library type, supporting master-copy operations for sharing content. Alarms are managed through `PlcAlarmTextProvider` and alarm text lists (`PlcAlarmUserTextlist`). Safety applications expose `SafetyAdministration` with runtime groups and attribute access. Units are managed via `PlcUnitProvider` for both standard and safety unit definitions.

## Required Namespaces

```csharp
using Siemens.Engineering.Library;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Alarm;
using Siemens.Engineering.Safety;
using Siemens.Engineering.SW.Units;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`
- `Siemens.Engineering.Safety.dll`

## Common Patterns

### Create UserGlobalLibrary

**Description:** Create a new user global library at a specified directory location. The `TiaPortal.GlobalLibraries` collection provides a generic `Create<T>` method for creating library instances.

**Example:**

```csharp
var globalLibrary = TiaPortalInstance.GlobalLibraries.Create<UserGlobalLibrary>(destination, "newLibrary");
```

**Key Types and Methods:**
- `TiaPortal.GlobalLibraries` — collection of global libraries
- `GlobalLibraryCollection.Create<T>(DirectoryInfo, string)` — creates a new library instance

### Close Library

**Description:** Close an open library to release its resources. Always close libraries when they are no longer needed to avoid file locks.

**Example:**

```csharp
globalLibrary.Close();
```

**Key Types and Methods:**
- `UserGlobalLibrary.Close()` — closes the library and releases resources

### MasterCopy to Library

**Description:** Create a master copy of an engineering object (e.g., alarm text list, block) inside a library. Master copies enable content sharing between the library and projects that reference it.

**Example:**

```csharp
var copy = globalLibrary.MasterCopyFolder.MasterCopies.Create(alarmTextList);
```

**Key Types and Methods:**
- `UserGlobalLibrary.MasterCopyFolder` — root folder for master copies
- `MasterCopyCollection.Create(IEngineeringObject)` — creates a master copy from an engineering object

### Get PlcAlarmTextProvider

**Description:** Retrieve the `PlcAlarmTextProvider` service from `PlcSoftware` to access alarm-related functionality.

**Example:**

```csharp
var alarmTextProvider = plcSoftware.GetService<PlcAlarmTextProvider>();
```

**Key Types and Methods:**
- `PlcAlarmTextProvider` — service for alarm text management

### Access Alarm Text Lists

**Description:** Access alarm text lists from the `PlcAlarmTextlistGroup`. Filter by name to find specific alarm text lists (e.g., standard user alarm text lists like "USER_1").

**Example:**

```csharp
var alarmTextList = plcSoftware.PlcAlarmTextlistGroup.PlcAlarmUserTextlists
    .FirstOrDefault(x => x.Name == "USER_1");
```

**Key Types and Methods:**
- `PlcSoftware.PlcAlarmTextlistGroup` — root container for alarm text lists
- `PlcAlarmTextlistGroup.PlcAlarmUserTextlists` — collection of user alarm text lists

### Read SafetyAdministration and RuntimeGroups

**Description:** Access safety configuration from the CPU via `SafetyAdministration`. Enumerate runtime groups and read their attributes (e.g., main safety block name and DB name).

**Example:**

```csharp
var safetyAdmin = cpu.GetService<SafetyAdministration>();
var runtimeGroup = safetyAdmin.RuntimeGroups.First();
var mainSafetyBlockName = runtimeGroup.GetAttribute("MainSafetyBlockName");
var mainSafetyDbName = runtimeGroup.GetAttribute("MainSafetyBlockIDbName");
```

**Key Types and Methods:**
- `SafetyAdministration` — service for safety configuration management
- `SafetyAdministration.RuntimeGroups` — collection of runtime groups
- `RuntimeGroup` — represents a safety runtime group
- `RuntimeGroup.GetAttribute(string)` — retrieves attribute values by name

### Access PlcUnitProvider and Units

**Description:** Retrieve the `PlcUnitProvider` service to access both standard and safety unit definitions. Units provide measurement unit support for engineering objects.

**Example:**

```csharp
var plcUnitProvider = plcSoftware.GetService<PlcUnitProvider>();
var safetyUnits = plcUnitProvider.UnitGroup.SafetyUnits;
var units = plcUnitProvider.UnitGroup.Units;
```

**Key Types and Methods:**
- `PlcUnitProvider` — service for unit management
- `PlcUnitGroup.Units` — collection of standard units
- `PlcUnitGroup.SafetyUnits` — collection of safety-specific units

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `GlobalLibraries.Create<UserGlobalLibrary>()` | Create a new user global library |
| `UserGlobalLibrary.Close()` | Close and release a library |
| `MasterCopyFolder.MasterCopies.Create()` | Create a master copy in a library |
| `plcSoftware.GetService<PlcAlarmTextProvider>()` | Get the alarm text provider |
| `PlcAlarmTextlistGroup.PlcAlarmUserTextlists` | Access user alarm text lists |
| `cpu.GetService<SafetyAdministration>()` | Get safety administration from CPU |
| `RuntimeGroup.GetAttribute(name)` | Read a runtime group attribute |
| `plcSoftware.GetService<PlcUnitProvider>()` | Get the unit provider |

## Related Files

- [`blocks`](../blocks/SKILL.md) — libraries can contain reusable blocks
- [`tags-and-tagtables`](../tags-and-tagtables/SKILL.md) — libraries can export tags to projects
- [`online-and-download`](../online-and-download/SKILL.md) — library content is downloaded as part of the PLC software

## Exception Handling

- `EngineeringException` is thrown when creating master copies if the library is not open or the source object is already a master copy
- `InvalidOperationException` may occur if the library file is locked by another process
- Always verify that the library is open (not closed) before performing master copy operations
- Null checks should be performed after accessing alarm text lists, as user-defined lists may not exist in all projects
