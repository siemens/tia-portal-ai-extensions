---
name: technology-objects
description: Technology Objects (TOs) for motion control in TIA Portal. Use when creating, finding, and configuring Technology Objects like speed axes, positioning axes, and setting TO parameters.
metadata:
  siemens-depends-on: "openness-base, engineering-objects"
---

# Technology Objects

## Overview

Technology Objects (TOs) are parameterized function blocks in TIA Portal that represent drive technologies such as speed axes, positioning axes, and cam control. They are managed under `PlcSoftware.TechnologicalObjectGroup` and provide a structured way to configure motion control functionality through typed parameters.

## Required Namespaces

```csharp
using Siemens.Engineering.HW;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.TechnologicalObjects;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`

## Common Patterns

### Create TechnologyObject

**Description:** Create a new Technology Object of a specified type (e.g., `TO_SpeedAxis`, `TO_PositioningAxis`) within the PLC Software's TechnologicalObjectGroup. Always check for an existing TO before creating — `Create` does not replace.

**Example:**

```csharp
var plcDevice = Project.Devices.First(x => x.Name == "PLC_S120Democase");
var plcSoftware = plcDevice.DeviceItems[1].GetService<SoftwareContainer>().Software as PlcSoftware;

const string NameOfTo = "ABC";
const string TypeOfTo = "TO_SpeedAxis";
Version versionOfTo = new(6, 0);

// Check existence before creating
var existing = plcSoftware.TechnologicalObjectGroup.TechnologicalObjects
    .FirstOrDefault(t => t.GetAttribute("Name")?.ToString() == NameOfTo);
if (existing == null)
    plcSoftware.TechnologicalObjectGroup.TechnologicalObjects
        .Create(NameOfTo, TypeOfTo, versionOfTo);
```

**Key Types and Methods:**
- `PlcSoftware.TechnologicalObjectGroup` — container for all Technology Objects in the PLC software; always at PLC root (never inside a SW-Unit)
- `TechnologicalObjectCollection.Create(string name, string type, Version version)` — creates a new TO
- TOs are **not supported in SW-Units** — always use the root `PlcSoftware.TechnologicalObjectGroup`

### Navigate TO Sub-Groups

**Description:** TOs have their own group hierarchy under `PlcSoftware.TechnologicalObjectGroup`. Use `Groups.Find`/`Groups.Create` to build sub-folder paths.

**Example:**

```csharp
TechnologicalInstanceDBGroup GetOrCreateToGroup(
    TechnologicalInstanceDBGroup rootGroup, IEnumerable<string> segments)
{
    var current = rootGroup;
    foreach (var segment in segments)
        current = current.Groups.Find(segment) ?? current.Groups.Create(segment);
    return current;
}
```

**Key Types and Methods:**
- `TechnologicalInstanceDBGroup` — TO group type (root and sub-groups)
- `TechnologicalInstanceDBGroup.Groups` — sub-group composition

### Place TO from Library MasterCopy

**Description:** Technology Objects stored in a GlobalLibrary appear as `TechnologicalInstanceDB` content in MasterCopies. Route them to `TechnologicalObjectGroup.TechnologicalObjects.CreateFrom` — **not** to `BlockGroup.Blocks.CreateFrom`. TOs always live at PLC root; SW-Units have no `TechnologicalObjectGroup`.

**Example:**

```csharp
// ContentType == "TechnologicalInstanceDB"
var toGroup = GetOrCreateToGroup(plcSoftware.TechnologicalObjectGroup, targetGroupSegments);
toGroup.TechnologicalObjects.CreateFrom(mc, MasterCopyMode.ThrowIfExists);
```

**Key Types and Methods:**
- `TechnologicalObjectComposition.CreateFrom(MasterCopy, MasterCopyMode)` — places a TO from a MasterCopy
- `MasterCopyMode.ThrowIfExists` — throws if a TO with the same name already exists

### Find TechnologyObject by Name

**Description:** Retrieve an existing Technology Object from the collection by its name. This is the standard approach before reading or modifying parameters.

**Example:**

```csharp
var plc = Project.Devices.First(x => x.Name == "PLC_S120Democase");
var cpu = plc.DeviceItems.Single(x => x.Classification == DeviceItemClassifications.CPU);

var plcSoftware = cpu.GetService<SoftwareContainer>().Software as PlcSoftware;
var to = plcSoftware.TechnologicalObjectGroup.TechnologicalObjects
    .First(x => x.Name == "PositioningAxis_blue");
```

**Key Types and Methods:**
- `TechnologicalObject.Name` — the display name of the Technology Object.
- `TechnologicalInstanceDB` — the instance DB associated with the TO.

### ⚠️ TO type/version is installation-specific — do not hardcode a fixed version

**Description:** The `Version` accepted by `TechnologicalObjects.Create(name, type, version)` must match a version actually registered in the local TIA Portal installation's Startdrive/Technology libraries. Documented example versions (e.g. `1.0`–`6.0`) are **not guaranteed to exist** on every installation — one confirmed data point: on TIA Portal V21, `TO_PositioningAxis` required version `"10.0"`; versions `1.0`–`9.0`, `11.0`, and `12.0` all failed with "does not exist or is not a valid technology object". There is no known Openness API to enumerate valid TO type/version combinations up front — if the exact version is unknown, cascade-probe candidate versions and catch the exception.

**Example:**

```csharp
TechnologicalObject CreateWithVersionProbe(TechnologicalObjectComposition group,
    string name, string type, IEnumerable<double> candidateVersions)
{
    foreach (var v in candidateVersions.OrderByDescending(x => x))
    {
        try
        {
            return group.Create(name, type, new Version((int)v, (int)((v - (int)v) * 10)));
        }
        catch (Exception)
        {
            // try the next candidate
        }
    }
    throw new InvalidOperationException(
        $"No compatible version of '{type}' found among candidates {string.Join(", ", candidateVersions)}.");
}
```

**Key points:**
- Never assume a fixed version number from an example is valid on the target machine.
- If the user/context doesn't supply a known-good version, probe from the highest plausible candidate downward rather than guessing a single value.
- Known good data point: TIA Portal **V21 → `TO_PositioningAxis` → version `10.0`**.

### Set TechnologyObject Parameters

**Description:** Modify configuration parameters of a Technology Object using dot-notation parameter paths. Parameters accept various value types including `bool`, `PlcTag`, and primitive types. Use `Parameters.Find(string path)` to locate a specific parameter, then assign to its `.Value` property.

**Example:**

```csharp
var plcSoftware = cpu.GetService<SoftwareContainer>().Software as PlcSoftware;
var technologyObject = plcSoftware.TechnologicalObjectGroup.TechnologicalObjects
    .First(x => x.Name == "PositioningAxis_blue");

if (technologyObject == null)
{
    Console.WriteLine("TO not found");
    return;
}

// Set a boolean parameter
technologyObject.Parameters.Find("Actor.InverseDirection").Value = true;

// Set hardware limits active
technologyObject.Parameters.Find("PositionLimits_HW.Active").Value = true;

// Set a parameter that accepts a PlcTag (connected tag reference)
var connectedTag = plcSoftware.TagTableGroup.TagTables
    .First(x => x.Name.ToLower().Contains("default")).Tags.Find("test");
technologyObject.Parameters.Find("_PositionLimits_HW.MinSwitchAddress").Value = connectedTag;
```

**Key Types and Methods:**
- `TechnologicalObject.Parameters` — collection of all parameters exposed by the TO.
- `TechnologicalParameter.Find(string)` — locates a parameter by its full dot-notation path (e.g., `"Actor.InverseDirection"`).
- `TechnologicalParameter.Value` — get/set the parameter value; accepts `bool`, `PlcTag`, and other typed values depending on the parameter definition.

### ⚠️ Connect a TO to its drive axis — `AxisHardwareConnectionProvider` (not `Actor.*` parameters)

**Description:** Connecting a positioning/speed axis Technology Object to its drive's hardware I/O is **not** done by setting `Actor.Type` or any other `Actor.*` `TechnologicalParameter` value directly — that write succeeds without throwing but does **not** create a real hardware connection, producing a convincing false-positive ("no exception thrown", looks configured) while the drive remains unconnected in the TIA Portal GUI. The real, verified API is `AxisHardwareConnectionProvider` obtained via `GetService<T>()` on the `TechnologicalObject`, using its `ActorInterface.Connect(...)` with byte addresses derived from the telegram's I/O addresses.

**Example:**

```csharp
using Siemens.Engineering.SW.TechnologicalObjects;

var provider = technologyObject.GetService<AxisHardwareConnectionProvider>();
var actorInterface = provider.ActorInterface; // AxisEncoderHardwareConnectionInterface

// IMPORTANT: filter Telegram.Addresses by direction — do NOT index by position.
// Addresses[0]/Addresses[1] can return the same StartAddress for both directions.
// `IoType` is used here as a strongly-typed property (as seen via reflection on this
// project's SDK version); if direct property access fails on your installation, fall
// back to `a.GetAttribute("IoType")` and verify the actual member via reflection.
var inputAddr  = telegram.Addresses.First(a => a.IoType == AddressIoType.Input);
var outputAddr = telegram.Addresses.First(a => a.IoType == AddressIoType.Output);

// IMPORTANT: StartAddress is NOT a raw byte address — multiply by 8 to get the
// PLC I/O byte address the Connect(...) overload expects. (Confirmed direction:
// multiply, not divide — dividing was tried first and is wrong.)
int inputByteAddress  = (int)inputAddr.GetAttribute("StartAddress") * 8;
int outputByteAddress = (int)outputAddr.GetAttribute("StartAddress") * 8;

actorInterface.Connect(inputByteAddress, outputByteAddress, ConnectOption.Default);

// ALWAYS verify — a successful call is not proof of a real connection.
bool isConnected = actorInterface.IsConnected;
if (!isConnected)
    throw new InvalidOperationException("Connect() returned without exception but IsConnected is false.");
```

**Key Types and Methods:**
- `TechnologicalObject.GetService<AxisHardwareConnectionProvider>()` — entry point for the TO↔drive hardware connection
- `AxisHardwareConnectionProvider.ActorInterface` — `AxisEncoderHardwareConnectionInterface` used to connect/verify
- `AxisEncoderHardwareConnectionInterface.Connect(int inputAddress, int outputAddress, ConnectOption)` — the real connection call
- `Address.IoType` (`AddressIoType.Input` / `.Output`) — filter, never index, telegram addresses; confirmed via reflection in this workflow, not documented elsewhere in the SDK — verify via `GetAttribute("IoType")` if direct property access fails on your installation
- `Address.StartAddress * 8` — bit/word-index → PLC I/O byte address conversion required by `Connect(...)`
- `IsConnected` / `InputAddress` / `OutputAddress` on `ActorInterface` — read these back to verify a connection actually succeeded

**🛑 Anti-pattern — silent false success:**

```csharp
// WRONG — sets a parameter, throws no exception, but does NOT connect the drive.
technologyObject.Parameters.Find("Actor.Type").Value = someValue;
```

Never treat "no exception was thrown" as proof that a hardware connection was made for this or any TO↔drive wiring step. Always confirm via `IsConnected`/`InputAddress`/`OutputAddress` on the `ActorInterface` after calling `Connect(...)`.

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `TechnologicalObjectCollection.Create(name, type, version)` | Create a new Technology Object |
| `GetService<AxisHardwareConnectionProvider>().ActorInterface.Connect(in, out, opt)` | Connect a TO to its drive axis hardware (verify with `IsConnected`) |
| `TechnologicalObjects.FirstOrDefault(x => ...)` | Find an existing TO (always check before creating) |
| `GetOrCreateToGroup(rootGroup, segments)` | Navigate or build a TO sub-group path |
| `toGroup.TechnologicalObjects.CreateFrom(mc, ...)` | Place a TO from a MasterCopy |
| `Parameters.Find("path.to.param")` | Locate a TO parameter by dot-notation path |
| `TechnologicalParameter.Value = ...` | Set the value of a TO parameter |
| `PlcSoftware.TechnologicalObjectGroup` | Access the TO container — always at PLC root |

## Related Files

- [`global-library`](../global-library/SKILL.md) — MasterCopy routing including `TechnologicalInstanceDB` content type
- [`blocks`](../blocks/SKILL.md) — Program blocks, OBs, FCs, FBs, and DBs
- [`security`](../security/SKILL.md) — Security and access control
- [`tags-and-tagtables`](../tags-and-tagtables/SKILL.md) — Tag table management and symbol creation
- [`devices-and-hardware`](../devices-and-hardware/SKILL.md) — Device and hardware configuration
- [`telegrams`](../telegrams/SKILL.md) — `Telegram.Addresses`/`IoType`/`StartAddress` used when connecting a TO to its drive axis
- [`drive-objects`](../drive-objects/SKILL.md) — the drive-side `DriveObject`/`Telegrams` that the TO's hardware connection targets

## Exception Handling

- **TO not found:** `TechnologicalObjectCollection.First(...)` throws `InvalidOperationException` if no TO matches. Always verify existence with `.FirstOrDefault()` before accessing parameters.
- **Invalid parameter path:** `Parameters.Find(string)` returns `null` if the path does not match any parameter. Check for `null` before accessing `.Value`.
- **Type mismatch on `.Value` assignment:** Assigning an incompatible type throws. Ensure the value type matches the parameter's expected type.
- **TO type/version not available:** If the specified TO type or version is not installed, `Create()` may return `null` or throw. Verify the required Startdrive libraries are added to the project — versions are installation-specific, so probe candidates rather than hardcoding one from documentation.
- **TO in SW-Unit:** TOs are not supported in SW-Units. Always place them at PLC root via `PlcSoftware.TechnologicalObjectGroup`.
- **`Actor.*` parameter writes look successful but do not connect hardware:** setting `Actor.Type` or other `Actor.*` `TechnologicalParameter` values never throws, but also never wires the drive. Use `AxisHardwareConnectionProvider.ActorInterface.Connect(...)` and verify with `IsConnected` instead.
