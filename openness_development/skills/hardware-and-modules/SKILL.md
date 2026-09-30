---
name: hardware-and-modules
description: Hardware and module management for SINAMICS drives. Use when plugging new hardware, changing module types, searching hardware catalog, projecting motor/encoder configurations, and managing master copies.
metadata:
  siemens-depends-on: "openness-base, devices-and-hardware"
---

# Hardware and Modules

## Overview

Hardware and module management in TIA Portal Openness covers inserting, replacing, deleting, and configuring SINAMICS hardware — motor modules, motors, encoders, and gearboxes. Use `PlugNew()` to insert hardware by `TypeIdentifier`, `ChangeType()` to replace module types, and the `HardwareCatalog` to search available products. Motor and encoder configuration is projected through `HardwareProjection`.

## 🛑 MANDATORY CHECK BEFORE CODING: TypeIdentifier Requirement

**BEFORE you write ANY code that creates hardware, you MUST ask the user for the `TypeIdentifier` of every hardware item they want to create.**

This is a **blocking requirement** — do NOT proceed to generate code without confirmed TypeIdentifiers.

### When to Ask

Ask the user for TypeIdentifiers when they request ANY of the following:
- Creating a device (S120, G115D, S7-1200, S7-1500, ET 200, etc.)
- Plugging a motor module (Single, Double)
- Plugging a motor (1FK7, etc.)
- Plugging an encoder
- Plugging an infeed (SLM, ALM, BLM)
- Plugging any hardware module (CBE20, VSM, terminal modules, etc.)

### How to Ask

Use the `ask_user` tool with a clear message. Example:

```
I need the TypeIdentifier for the hardware you want to create.

To find the TypeIdentifier in TIA Portal:
1. Go to Options → Settings → Hardware Configuration
2. Enable "Display of the Type Identifier"
3. Browse to the hardware module in the catalog
4. Copy the TypeIdentifier (e.g., OrderNumber:6SL3224-0BE32-0UA0/V2.9)

What TypeIdentifiers should I use for:
- [list each item needed]?
```

### What You Must NOT Do

- ❌ Do NOT assume or guess TypeIdentifiers
- ❌ Do NOT use example TypeIdentifiers from this documentation in production code
- ❌ Do NOT skip asking just because the user mentioned a product name (e.g., "S120", "1FK7") — the exact TypeIdentifier includes version info that is required
- ❌ Do NOT start generating code before you have all TypeIdentifiers

## Required Namespaces

```csharp
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.MC.Drives;
using Siemens.Engineering.MC.Drives.DFI;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`
- `Siemens.Engineering.Startdrive.dll`

## Common Patterns

### PlugNew — Insert Hardware Module by TypeIdentifier

**Description:** Plug a new hardware module (motor module, motor, etc.) into a device or drive axis using an order number / `TypeIdentifier`. Specify the item name and slot number.

**Example:**

```csharp
var motorModule = device.PlugNew("OrderNumber:6SL3120-1TE15-0Axx//10002", "MotorModule", 65535);
var motor = axisRack?.PlugNew("OrderNumber:1FK7011-xAK21-xTGx", "", 65535);
```

**Key Types and Methods:**
- `Device.PlugNew(typeIdentifier, name, slot)` — insert hardware at device level
- `DeviceItem.PlugNew(typeIdentifier, name, slot)` — insert hardware under a specific device item
- `TypeIdentifier` — string in format `"OrderNumber:<MLFB>"` or `"OrderNumber:<MLFB>//<version>"`

---

### ⚠️ PlugNew Hierarchy Rules for StartDrive (SINAMICS Devices)

When plugging hardware into StartDrive (SINAMICS) devices, the correct parent object matters. Follow these rules:

| Hardware Type | Plug Location | Slot/Position | Notes |
|---|---|---|---|
| **Devices** (SINAMICS drives) | `Project.Devices` | N/A | Always created directly in the project |
| **Single Motor Modules (Axis)** | Device | 65535 | Plugged directly to the S120 Device |
| **Double Motor Modules** | Device | 65535 | Plugged directly to the S120 Device |
| **Infeeds** (Active/Basic/Smart Line Module) | Device | 65535 | Plugged directly to the S120 Device |
| **Terminal Boards (TB30)** | Device | 65535 | Plugged directly to the S120 Device |
| **Terminal Modules (TM15, TM31, TM41, TM120, TM150)** | Device | 65535 | Plugged directly to the S120 Device |
| **DriveCliq Hubs** | Device | 65535 | Plugged directly to the S120 Device |
| **Voltage Sensing Modules (VSM)** | DeviceItem of Infeeds | 65535 | **Warning:** `PlugNew` returns a DeviceItem one layer below the created module. To plug further children, get `.Parent` first |
| **Motors** | The axis's own rack `DeviceItem` (`TypeIdentifier` starts with `System:Rack`) | 65535 | Plug onto the axis rack, not onto the nested motor-module item |
| **Encoders** | Auto-created when the motor is plugged (for DRIVE-CLiQ motor families that expose integrated encoder items) | N/A | No separate encoder `PlugNew` call is needed for those motor families |
| **Communication Board (CBE20)** | Control Unit (first DeviceItem under S120) | **3** | NOT slot 65535 — use position **3** |

**Critical Warnings:**

1. **`PlugNew` Return Value Shift:** When you plug an object onto a created module (e.g., VSM on Infeed), the returned `DeviceItem` is **one layer below** the expected device item. To plug further objects onto this module, access the **parent** of the returned value:

   ```csharp
   var vsmResult = infeedDeviceItem.PlugNew("OrderNumber:6SL3210-1NE30-0UA0/V2.9", "VSM", 65535);
   var actualModule = vsmResult.Parent; // Get the actual module to plug further children
   ```

2. **CBE20 Position Number:** The Communication Board CBE20 uses position **3**, NOT the default 65535. Use the wrong position and the plug will fail.

   ```csharp
   var controlUnit = s120Device.DeviceItems.First(); // First device item = control unit
   var cbe20 = controlUnit.PlugNew("OrderNumber:6SL3265-0AA00-0FA0/V2.9", "CBE20", 3);
   ```

3. **Double Motor Module auto-creates two axis racks — plug DRIVE-CLiQ motors onto the axis rack, not the module:** Plugging a Double Motor Module onto the S120 `Device` automatically creates two **sibling** axis-rack `DeviceItem`s, one per physical axis of the module. Resolve the rack structurally from the axis `DriveObject` / owning `DeviceItem`; do not identify it by an auto-generated display name. Plugging a motor onto the nested motor-module `DeviceItem` or `DRIVE-CLiQ interface` child fails or attaches it in the wrong place.

   ```csharp
   DeviceItem axisRack = axisDriveObject.Parent<DeviceItem>()
       ?? throw new InvalidOperationException("The axis DriveObject has no owning DeviceItem.");
   var motorItem = axisRack.PlugNew(motorTypeIdentifier, "", 65535);
   ```

   A successful motor plug can auto-create additional sibling encoder-related `DeviceItem`s on that rack (for example measuring-system / encoder-evaluation items). For those motor families, no separate encoder `PlugNew` call is needed or possible. This integrated-encoder rule does not apply to separately projected third-party or external encoders: configure those with `HardwareProjection.GetCurrentEncoderConfiguration` and `ProjectEncoderConfiguration`. Validate motor placement by recursively searching **that axis rack** for the motor `TypeIdentifier`, rather than searching the whole CU device where both axes may use the same motor type.

### Devices.CreateWithItem — Create Device from Catalog

**Description:** Create a new device instance directly from a hardware catalog `TypeIdentifier`.

**Example:**

```csharp
var device = Project.Devices.CreateWithItem(s210TypeIdentifier, "S210_New", "S210_NewDevice");
var g115d = Project.Devices.CreateWithItem("OrderNumber:6SL3500-xxxxx-xFxx/4.7.14", "", "");
```

**Key Types and Methods:**
- `Devices.CreateWithItem(typeIdentifier, name, deviceName)` — create device from catalog entry
- `Project.Devices` — collection of devices in the project

### ChangeType — Replace Hardware Module Type

**Description:** Change the `TypeIdentifier` of an existing motor module via `DriveItemHardwareModule.ChangeType()`. Useful for swapping hardware variants without removing and reinserting.

**Example:**

```csharp
var driveItemModule = driveAxisModule.GetService<DriveItemHardwareModule>();
driveItemModule.ChangeType(newTypeIdentifier);
```

**Key Types and Methods:**
- `DriveItemHardwareModule` — service exposing hardware module properties
- `ChangeType(typeIdentifier)` — replaces the module type in place

### Delete DeviceItem

**Description:** Remove a device item from the hierarchy.

**Example:**

```csharp
existingMotor.Delete();
```

**Key Types and Methods:**
- `DeviceItem.Delete()` — permanently removes the item from the device tree

### HardwareCatalog.Find — Search All Entries

**Description:** Query the hardware catalog for entries matching a search string. An empty string returns all entries.

**Example:**

```csharp
var hardwareCatalog = TiaPortalInstance.HardwareCatalog.Find(string.Empty);
var hardwareCatalog = TiaPortalInstance.HardwareCatalog.Find("S120");
```

**Key Types and Methods:**
- `TiaPortalInstance.HardwareCatalog` — global access to the hardware catalog
- `HardwareCatalog.Find(searchString)` — search method accepting partial matches

### ⚠️ `CatalogEntry` property names — do not guess by analogy

**Description:** `CatalogEntry` objects returned from `HardwareCatalog.Find(...)` do **not** use the property names that seem intuitive by analogy with other Siemens Openness types. The confirmed property names are:

| Expected-but-wrong name | Actual property |
|---|---|
| `Name` | `TypeName` |
| `OrderNumber` | `ArticleNumber` |
| — | `TypeIdentifier` (use this to `PlugNew`/`CreateWithItem`) |
| — | `Version` |

```csharp
var entries = TiaPortalInstance.HardwareCatalog.Find("1FK7");
foreach (var e in entries)
{
    Console.WriteLine($"{e.TypeName} | {e.ArticleNumber} | {e.TypeIdentifier} | {e.Version}");
}
```

If a property access throws `RuntimeBinderException`/`MissingMemberException` or returns unexpected data, verify the actual member names via reflection against the running instance rather than assuming the pattern from other services.

### Auto-slot convention: pass `65535` to let TIA Portal pick the first free slot

**Description:** Most `PlugNew(typeIdentifier, name, slot)` calls onto a SINAMICS device (motor modules, infeeds, terminal boards, terminal modules, DriveCliq hubs, motors, encoders) accept the sentinel slot value **`65535`**, which tells TIA Portal to auto-select the first free slot rather than requiring the caller to know or compute an exact slot number. This convention is not self-evident from the API surface and is easy to miss without prior TIA Portal GUI knowledge — see the hierarchy table below for the (rare) explicit-slot exceptions such as CBE20 (slot `3`).

### HardwareCatalog Find + Filter for DriveCliq Motors

**Description:** Find catalog entries matching a keyword, then filter by `CatalogPath` for sub-category refinement (e.g., DriveCliq motors).

**Example:**

```csharp
var motorEntries = hardwareCatalog.Find("motors")
    .Where(x => x.CatalogPath != null && x.CatalogPath.ToLower().Contains("cliq"))
    .ToList();
```

**Key Types and Methods:**
- `CatalogPath` — hierarchical path string for catalog categorization
- `TypeIdentifier` — unique product identifier from catalog entries

### Master Copy Create & Recreate Device

**Description:** Create a master copy of a device, delete the original, then recreate from the master copy. Useful for device cloning workflows.

**Example:**

```csharp
var masterCopy = masterCopiesFolder.MasterCopies.Create(device);
device.Delete();
var newDevice = Project.Devices.CreateFrom(masterCopy);
```

**Key Types and Methods:**
- `MasterCopyFolder` — container for master copies
- `MasterCopies.Create(device)` — create a master copy snapshot
- `Devices.CreateFrom(masterCopy)` — instantiate a new device from the copy

### Project Third-Party Motor Configuration

**Description:** Get current motor configuration, modify required and optional entries, then project the configuration back to the drive.

**Example:**

```csharp
var hardwareProjection = driveObject.GetService<DriveFunctionInterface>().HardwareProjection;
var motorConfiguration = hardwareProjection.GetCurrentMotorConfiguration(0);
motorConfiguration.RequiredConfigurationEntries.ToList()
    .ForEach(ce => { ce.Value = ...; });
motorConfiguration.OptionalConfigurationEntries.ToList()
    .ForEach(ce => { ce.Value = ...; });
motorConfiguration.SetEquivalentCircuitDiagramData(false);
hardwareProjection.ProjectMotorConfiguration(motorConfiguration, 0);
```

**Key Types and Methods:**
- `HardwareProjection` — manages hardware configuration projection
- `MotorConfiguration.RequiredConfigurationEntries` — mandatory configuration entries
- `MotorConfiguration.OptionalConfigurationEntries` — optional configuration entries
- `ProjectMotorConfiguration(config, slot)` — applies the configuration

### Project Third-Party Encoder Configuration

**Description:** Get current encoder configuration, modify entries by name, then project back.

**Example:**

```csharp
var hardwareProjection = driveObject.GetService<DriveFunctionInterface>().HardwareProjection;
var encoderConfig = hardwareProjection.GetCurrentEncoderConfiguration(0);
encoderConfig.RequiredConfigurationEntries.ToList()
    .ForEach(ce => { ce.Value = ...; });
hardwareProjection.ProjectEncoderConfiguration(encoderConfig, 1);
```

> **Verification required:** This `0`/`1` pairing is preserved from the empirical example, but the two APIs' indexing semantics still require live V21 verification before reuse. Verify the intended encoder/configuration slot for the specific device; `0`/`0` is not confirmed.

**Key Types and Methods:**
- `GetCurrentEncoderConfiguration(slot)` — retrieves current encoder settings
- `ProjectEncoderConfiguration(config, slot)` — applies encoder configuration

### ⚠️ External Encoder Code-Number Selection (G2xx OM ENC/OM DQ) — via `ChangeType()`, NOT `HardwareProjection`

**Description:** For G2xx drives (e.g. G210) with an external, terminal-wired
encoder module (`OM ENC`/`OM DQ`), the "Measuring system - Selection"
property (parameter `p400`, e.g. code `3001` = "1024 HTL A/B R") **cannot**
be set through any `DriveObject`/`HardwareProjection` API — every one of
these fails with the same error, regardless of which `DriveObject` is used
(including the encoder module's *own* `DriveObjectContainer`, which is a
separate, easy-to-miss `DriveObject` distinct from the axis/rack one):
- `DriveObject.Parameters.Find("p400")` and the index-based
  `Parameters.Find(400, 0)` both return `null` (not writable this way;
  `ReadParameters.Find("p400")` works fine for *reading* the current value).
- `HardwareProjection.GetCurrentEncoderConfiguration(0)` /
  `SetEncoder(...)` throw `EngineeringTargetInvocationException`: *"An error
  occurred while setting the attribute Result Predicate MDD Reading
  (MC_ComponentDataInfo) failed is not false."* — this happens on **every**
  `DriveObject` tried, which is the tell that `HardwareProjection` simply
  doesn't support this hardware family (it targets DRIVE-CLiQ/catalog
  motor-integrated encoders, not terminal/HTL-TTL external encoder modules).

The working fix instead uses `ChangeType()` — the same mechanism as
"ChangeType — Replace Hardware Module Type" above — but called on the
**encoder `DeviceItem` itself** (e.g. `"OM ENC_1"`), with a generic
"encoder data input" `TypeIdentifier`. This mirrors how a third-party/data-input
motor is selected via `"OrderNumber:XMxxxxx-xxxxx-xxxx//Motor data
input-Induction motors"` (`XM` prefix): the encoder equivalent uses an `XE`
prefix, with the version suffix encoding the interface family and code
number.

**Example:**

```csharp
// omEncDeviceItem = the OM ENC_1 / OM DQ_1 DeviceItem (NOT a DriveObject)
var driveItemModule = omEncDeviceItem.GetService<DriveItemHardwareModule>();
// e.g. "1024 HTL A/B R" == code number 3001
driveItemModule.ChangeType("OrderNumber:XExxxxx-xxxxx-xxxx//HTL_TTL.3001");
```

**How this was found:** `GetAttributeInfos()` and `DeviceItems` (children)
on the encoder `DeviceItem` show nothing encoder-related — no "Measuring
system" child object and no matching attribute. The `DriveItemHardwareModule`
service (with a settable `TypeIdentifier`) was only discovered via the
schema-free `GetServiceInfos()` enumeration (see [`engineering-objects`](../engineering-objects/SKILL.md) /
[`object-tree-walking`](../object-tree-walking/SKILL.md)), which lists it as a service the encoder
`DeviceItem` itself exposes — not something reachable through
`GetAttributeInfos()` or child `DeviceItems`.

**Key Types and Methods:**
- `DeviceItem.GetService<DriveItemHardwareModule>()` — get the module-type
  service directly from the encoder `DeviceItem` (not from a `DriveObject`)
- `DriveItemHardwareModule.ChangeType("OrderNumber:XExxxxx-xxxxx-xxxx//<InterfaceFamily>.<CodeNumber>")` — selects the encoder code number in place

### Set SimoGear MLFB via Commissioning

**Description:** Set the SimoGear material number on a G115D drive.

**Example:**

```csharp
var dfi = driveObject.GetService<DriveFunctionInterface>();
dfi.Commissioning.SetSimoGearMlfb("2KJ8001-2EA10-3FG1-D0X");
```

**Key Types and Methods:**
- `Commissioning.SetSimoGearMlfb(mlfb)` — sets the SimoGear material number

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `PlugNew(typeId, name, slot)` | Insert a hardware module |
| `Devices.CreateWithItem(typeId, name, deviceName)` | Create device from catalog |
| `DriveItemHardwareModule.ChangeType(typeId)` | Replace module type in place |
| `DeviceItem.Delete()` | Remove device item |
| `HardwareCatalog.Find(searchString)` | Search hardware catalog |
| `MasterCopies.Create(device)` | Create master copy snapshot |
| `Devices.CreateFrom(masterCopy)` | Instantiate device from master copy |
| `GetCurrentMotorConfiguration(slot)` | Get motor configuration |
| `ProjectMotorConfiguration(config, slot)` | Apply motor configuration |
| `GetCurrentEncoderConfiguration(slot)` | Get encoder configuration |
| `ProjectEncoderConfiguration(config, slot)` | Apply encoder configuration |
| `omEncDeviceItem.GetService<DriveItemHardwareModule>().ChangeType("...//HTL_TTL.<code>")` | Select external encoder code number (G2xx OM ENC/OM DQ) — `HardwareProjection` does not support this hardware family |
| `Commissioning.SetSimoGearMlfb(mlfb)` | Set SimoGear material number |

## Related Files

- [`drive-objects`](../drive-objects/SKILL.md) — accessing `DriveObject` and `DriveFunctionInterface` required for commissioning
- [`networks-and-drivecliq`](../networks-and-drivecliq/SKILL.md) — network port wiring between hardware modules
- [`parameters`](../parameters/SKILL.md) — parameter-level hardware configuration
- [`telegrams`](../telegrams/SKILL.md) — data exchange configuration for plugged hardware

## Exception Handling

- `PlugNew()` throws if the `TypeIdentifier` is invalid or the slot is occupied. Validate the type identifier against the hardware catalog first.
- `ChangeType()` may fail if the new type is incompatible with existing connections. Disconnect ports before changing type.
- `Delete()` on a device item with active connections or references may throw `EngineeringException`. Clean up references before deletion.
- Hardware projection methods require the drive object to be properly configured. Call `GetCurrent*Configuration()` before modifying.
- If `HardwareProjection.GetCurrentEncoderConfiguration`/`SetEncoder` throws `"...Result Predicate MDD Reading (MC_ComponentDataInfo) failed is not false..."` regardless of which `DriveObject` is used, the drive's encoder is likely an external terminal-wired module (G2xx `OM ENC`/`OM DQ`) that `HardwareProjection` does not support — use `ChangeType()` on the encoder `DeviceItem`'s own `DriveItemHardwareModule` instead (see "External Encoder Code-Number Selection" above).
