---
name: drive-objects
description: Drive objects and DriveFunctionInterface for SINAMICS drives. Use when locating DriveObjects, setting telegrams, writing drive parameters (scalar, BiCo, bit, indexed, DFI motor/encoder), handling Double-MoMo drives, refreshing drive state after writes, or accessing/deactivating drive objects.
metadata:
  siemens-depends-on: "openness-base, hardware-and-modules"
---

# Drive Objects

## Overview

Drive objects are the core abstractions in SINAMICS drives (S120, G115D, etc.) exposed through the TIA Portal Openness API. The `DriveFunctionInterface` provides commissioning, activation, and type-handling capabilities. Access drive objects via `GetService<DriveObjectContainer>()` on a `DeviceItem`, then retrieve individual drive objects from the `DriveObjects` collection.

This skill covers retrieving the drive function interface, inspecting drive object types, activating/deactivating objects, and the standard access pattern across all Startdrive code.

## Required Namespaces

```csharp
using Siemens.Engineering;
using Siemens.Engineering.MC.Drives;
using Siemens.Engineering.MC.Drives.DFI;
using Siemens.Engineering.MC.Drives.Enums;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`
- `Siemens.Engineering.Startdrive.dll`

## Common Patterns

### Get DriveFunctionInterface from DeviceItem

**Description:** Retrieve the `DriveFunctionInterface` service from a drive object to access drive-level commissioning functions. This is the primary entry point for most drive operations.

**Example:**

```csharp
var driveFunctionInterface = s120.DeviceItems[3]
    .GetService<DriveObjectContainer>()
    .DriveObjects.First()
    .GetService<DriveFunctionInterface>();
```

**Key Types and Methods:**
- `DriveObjectContainer` — service containing the collection of drive objects on a device item
- `DriveFunctionInterface` — provides access to commissioning, hardware projection, safety, and activation
- `GetService<T>()` — generic method on `DeviceItem` to retrieve a typed service

### DriveObjectTypeHandler — Read Current & Possible Types

**Description:** Access the `DriveObjectTypeHandler` to inspect the current drive object type and enumerate all possible types the object can assume.

**Example:**

```csharp
var driveObjectTypeHandler = driveFunctionInterface.DriveObjectFunctions.DriveObjectTypeHandler;
var currentType = driveObjectTypeHandler.CurrentDriveObjectType;
var possibleDriveObjectTypesList = driveObjectTypeHandler.PossibleDriveObjectTypes
    .Select(x => x.Name)
    .ToList();
```

**Key Types and Methods:**
- `DriveObjectTypeHandler` — manages the drive object type lifecycle
- `CurrentDriveObjectType` — the currently assigned type
- `PossibleDriveObjectTypes` — collection of all types available for this object

### Change DriveObject Activation State

**Description:** Activate or deactivate a drive object via `DriveObjectActivation.ChangeActivationState()`. Deactivation is often required before hardware or parameter changes.

**Example:**

```csharp
var driveObject = drive.DeviceItems
    .Single(x => x.Name == "BlueAxis")
    .GetService<DriveObjectContainer>()
    .DriveObjects.First();
var dfi = driveObject.GetService<DriveFunctionInterface>();
dfi.DriveObjectFunctions.DriveObjectActivation
    .ChangeActivationState(DriveObjectActivationState.Deactivate);
```

**Key Types and Methods:**
- `DriveObjectActivation` — manages activation state transitions
- `DriveObjectActivationState.Deactivate` / `Activate` — enum values for state changes
- `ChangeActivationState()` — performs the state transition

### Access DriveObject via GetService<DriveObjectContainer>

**Description:** The standard pattern to access a `DriveObject` from any `DeviceItem`. Filter by classification (e.g., `HM` for head module) or by name.

**Example:**

```csharp
var driveObject = g115d.DeviceItems
    .Single(x => x.Classification == DeviceItemClassifications.HM)
    .GetService<DriveObjectContainer>()
    .DriveObjects.First();
```

**Key Types and Methods:**
- `DeviceItemClassifications.HM` — classification constant for head modules
- `DriveObjectContainer.DriveObjects` — collection of drive objects
- `GetService<DriveObjectContainer>()` — primary accessor for all drive-related services

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `GetService<DriveObjectContainer>()` | Access drive objects on a DeviceItem |
| `GetService<DriveFunctionInterface>()` | Retrieve commissioning & activation APIs |
| `DriveObjectTypeHandler.CurrentDriveObjectType` | Read current drive object type |
| `DriveObjectTypeHandler.PossibleDriveObjectTypes` | Enumerate assignable types |
| `DriveObjectActivation.ChangeActivationState()` | Activate or deactivate a drive object |
| `DeviceItemClassifications.HM` | Filter device items by head module classification |

---

## Verified Operational Rules

### 1. `DriveObjectContainer` is the gateway — always via `DeviceItem.GetService<DriveObjectContainer>()`

A `DriveObject` is never returned directly by the hardware tree. It lives inside a `DriveObjectContainer` service on a specific `DeviceItem` whose `TypeIdentifier` starts with `"System:Rack"`.

```csharp
// Correct
DeviceItem doDeviceItem = /* DeviceItem with TypeIdentifier starting "System:Rack" */;
DriveObject driveObject = doDeviceItem
    .GetService<DriveObjectContainer>()
    ?.DriveObjects.FirstOrDefault();

// Wrong — iterating Device.DeviceItems and calling GetService<DriveObject>() directly
// Wrong — assuming the first DeviceItem in a Device is the DO
```

---

### 2. Locate the DO `DeviceItem` by `TypeIdentifier.StartsWith("System:Rack")`

When walking a device hierarchy to find the correct `DeviceItem` to call `GetService<DriveObjectContainer>()` on:

- Filter `Device.DeviceItems` (recursively) for items where `TypeIdentifier.StartsWith("System:Rack")` and `GetService<DriveObjectContainer>()` returns non-null.
- **CU (Control Unit) drives:** the placed object may be a `Device`, and that device can expose **multiple sibling** `System:Rack*` items — one per plugged drive component. Do **not** use `FirstOrDefault(...)` to grab "the" rack item.
- Enumerate **all** sibling `DeviceItem`s whose `TypeIdentifier` starts with `"System:Rack"` and whose `GetService<DriveObjectContainer>()` is non-null, then select the rack that structurally matches the component you care about. For example, a Double Motor Module axis rack is the one whose **direct child** `DeviceItem` has the module's `TypeIdentifier`.
- **HM classification:** if `DeviceItem.Classification == DeviceItemClassifications.HM`, it is a Control Unit head module — inspect its sibling `System:Rack*` items on the same parent `Device` and select the one whose container/children match the target component.
- If you do not yet know which component owns the target `DriveObject`, search or aggregate across **every** matching rack container instead of assuming there is one shared container for the whole CU device.

---

### 3. Double-MoMo: the `_2` name suffix selects the second drive object

When an attribute name ends with `_2` (e.g. `MainTelegram_2`), the operation targets the **second** drive object of a Double-MoMo (two-axis) drive, not the primary one. Identify it by finding a sibling `DeviceItem` (same parent `Device`, `TypeIdentifier.StartsWith("System:Rack")`) whose sub-`DeviceItem` at `PositionNumber == 200` has the **same `Name` and `TypeIdentifier`** as the primary DO's sub-item at position 200.

---

### 4. Telegram ordering: `MainTelegram` must be set before `SafetyTelegram`

TIA Portal rejects or silently ignores a `SafetyTelegram` insert/change if no `MainTelegram` is already present. Always process telegrams in the fixed order:

| Order | Type |
|---|---|
| 1 | `MainTelegram` |
| 2 | `SafetyTelegram` |
| 3 | `AdditionalTelegram` |
| 4 | `SupplementaryTelegram` |
| 5 | `TorqueTelegram` |
| 6 | `EdgeTelegram` |

---

### 5. Telegram insert/change pattern: always call `CanInsert`/`CanChange` before mutating

```csharp
TelegramComposition telegrams = driveObject.Telegrams;
Telegram telegram = telegrams.Find(telegramType);

if (telegram is null)
{
    if (!telegrams.CanInsertTelegram(telegramNumber, telegramType)) return; // fail
    telegrams.InsertTelegram(telegramNumber, telegramType);
    telegrams = driveObject.Telegrams;       // re-fetch after insert
    telegram  = telegrams.Find(telegramType);
}

if (telegram.TelegramNumber != telegramNumber)
{
    if (!telegram.CanChangeTelegram(telegramNumber)) return; // fail
    telegram.TelegramNumber = telegramNumber;
}

// Resize (discover minimum size by probing downward, then apply target)
int minInput = currentInput;
while (telegram.CanChangeSize(AddressIoType.Input, minInput - 1, false) && minInput > 0)
    minInput--;
if (!telegram.CanChangeSize(AddressIoType.Input, targetSize, false)) return; // fail
telegram.ChangeSize(AddressIoType.Input, targetSize, false);
```

`AdditionalTelegram` uses a different insert API: `CanInsertAdditionalTelegram(inputSize, outputSize)` / `InsertAdditionalTelegram(inputSize, outputSize)`.

---

### 6. `DriveParameter.Value` must be assigned the correct boxed CLR type — not a string

The API throws or silently ignores writes if the boxed type of `Value` does not match the parameter's native type. Read the current value's runtime type, convert the string to that type, then assign.

```csharp
string normalized = newValue.Replace(',', '.');   // normalise decimal separator
string typeName   = driveParameter.Value.GetType().ToString().Split('.').Last();
driveParameter.Value = typeName switch
{
    "UInt16" => Convert.ToUInt16(normalized, CultureInfo.GetCultureInfo("en-US")),
    "Int16"  => Convert.ToInt16(normalized,  CultureInfo.GetCultureInfo("en-US")),
    "UInt32" => Convert.ToUInt32(normalized, CultureInfo.GetCultureInfo("en-US")),
    "Int32"  => Convert.ToInt32(normalized,  CultureInfo.GetCultureInfo("en-US")),
    "Single" => Convert.ToSingle(normalized, CultureInfo.GetCultureInfo("en-US")),
    "Byte"   => Convert.ToByte(normalized,   CultureInfo.GetCultureInfo("en-US")),
    _        => normalized,
};

// Anti-pattern — assigning the raw string directly
driveParameter.Value = newValue;  // WRONG: throws "The type of the argument" exception
```

Skip the write if the value is already correct:
```csharp
if (driveParameter.Value.ToString().Equals(normalized)) return;
```

---

### 7. Force the TIA UI language to `en-US` before writing drive parameters

Drive parameter values containing decimal numbers are parsed by TIA Portal using the current UI language's number format. Writing `"3.14"` while the UI is set to German (`de-DE`) silently produces wrong results. Switch before the write loop and restore after.

```csharp
TiaPortalSetting langSetting = tiaPortal.SettingsFolders.Find("General")
    ?.Settings.Find("UserInterfaceLanguage");
CultureInfo? original = langSetting?.Value as CultureInfo;

if (original?.Name is not "en-US")
    langSetting.Value = new CultureInfo("en-US");

try { /* write all parameters */ }
finally
{
    if (original?.Name is not "en-US")
        langSetting.Value = original;
}
```

To get `TiaPortal` from a `ProjectBase`, walk up the parent chain:
`parent = project.Parent` until `parent is TiaPortal`.

---

### 8. Refresh the `DriveObject` after each successful parameter write

The `DriveObject` reference becomes stale after a write. Re-fetch from the container after every successful write.

```csharp
// After a successful write:
driveObject = doDeviceItem
    .GetService<DriveObjectContainer>()
    .DriveObjects.SingleOrDefault();
```

---

### 9. BiCo parameter assignment: assign the source `DriveParameter` object, not a string

For BiCo (binary interconnect) wiring, `driveParameter.Value` must be set to **another `DriveParameter` object**.

```csharp
// Same-DO BiCo
DriveParameter source = driveObject.Parameters.Find(biCoParamName);

// Cross-DO BiCo (value format "NeighborDOName:pXXX")
// → find sibling DeviceItem, get its DriveObject, then Parameters.Find(biCoParamName)
DriveParameter source = neighborDriveObject.Parameters.Find(biCoParamName);

targetDriveParameter.Value = source;   // correct
targetDriveParameter.Value = "p840";   // WRONG — string, not DriveParameter
```

---

### 10. Bit sub-parameter lookup: use `DriveParameter.Bits.Find(fullDotName)`

For bit parameters (e.g. `p840.1`), resolve the main parameter first, then call `.Bits.Find()` with the full dotted name.

```csharp
DriveParameter main    = driveObject.Parameters.Find("p840");
DriveParameter bitParam = main.Bits.Find("p840.1");  // full name, not just "1"

// Wrong — top-level Find does not walk Bits
driveObject.Parameters.Find("p840.1");  // returns null
```

---

### 11. `p105` (DO activation state) uses `DriveFunctionInterface.DriveObjectActivation`, not `DriveParameter.Value`

```csharp
driveObject.GetService<DriveFunctionInterface>()
    .DriveObjectFunctions
    .DriveObjectActivation
    .ChangeActivationState(DriveObjectActivationState.Activate); // 0=Deactivate, 1=Activate, 2=DeactivateAndNotPresent

// Wrong
driveObject.Parameters.Find("p105").Value = 1;  // ignored or throws
```

---

### 12. Motor/encoder configuration: use `HardwareProjection` read-modify-write, not `DriveParameter.Value`

Motor parameters (p305, p311, p315, p316, p322, p323, p338, p341, p350, p356, and optional p312/p317–p320/p325/p326/p329/p348/p392/p393/p601) and encoder parameters (p404.x, p407, p408, p421–p449 family) must be set through the DFI `HardwareProjection` API.

```csharp
DriveFunctionInterface dfi = driveObject.GetService<DriveFunctionInterface>();
HardwareProjection hp = dfi.HardwareProjection;

// Motor
MotorConfiguration motorConfig = hp.GetCurrentMotorConfiguration(0);
// mutate motorConfig.RequiredConfigurationEntries / OptionalConfigurationEntries by Name
hp.ProjectMotorConfiguration(motorConfig, 0);

// Encoder
EncoderConfiguration encoderConfig = hp.GetCurrentEncoderConfiguration(0);
// mutate encoderConfig.RequiredConfigurationEntries by Name
hp.ProjectEncoderConfiguration(encoderConfig, 1);
```

> **Verification required:** This `0`/`1` pairing is preserved from the empirical example, but the two APIs' indexing semantics still require live V21 verification before reuse. Verify the intended encoder/configuration slot for the specific device; `0`/`0` is not confirmed. See `hardware-and-modules` for the detailed workflow.

Entry values follow the same boxed-CLR-type assignment rule as `DriveParameter.Value` (Rule 6).

---

### 13. Read-only parameters (`r`-prefix) are in `DriveObject.ReadParameters`, not `Parameters`

`r`-parameters (diagnostic/actual-value parameters) live in `DriveObject.ReadParameters`. `Parameters.Find("r21")` returns `null`. To distinguish "parameter not found" from "parameter exists but is read-only":

```csharp
if (driveObject.Parameters.Find(paramName) is null)
{
    if (driveObject.ReadParameters.Find(paramName) is not null)
        return Failure("Parameter is read-only (r-parameter)");
    else
        return Failure("Parameter not found");
}
```

---

## Anti-Patterns

| Anti-pattern | Why it fails | Correct alternative |
|---|---|---|
| `driveParameter.Value = "3.14"` | Type mismatch — `Value` requires boxed CLR type | Read `.Value.GetType()`, convert string, assign boxed value (Rule 6) |
| Setting `SafetyTelegram` before `MainTelegram` | API error / silently ignored | Sort by fixed telegram order before processing (Rule 4) |
| Reusing `DriveObject` reference after write | Reference goes stale | Re-fetch via `GetService<DriveObjectContainer>().DriveObjects.SingleOrDefault()` (Rule 8) |
| `driveObject.Parameters.Find("r21")` | r-parameters live in `ReadParameters` | Use `driveObject.ReadParameters.Find(name)` (Rule 13) |
| `driveObject.Parameters.Find("p840.1")` | Bit params not in top-level `Find` | `Parameters.Find("p840").Bits.Find("p840.1")` (Rule 10) |
| Setting p305/p311 via `DriveParameter.Value` | DFI parameters require `HardwareProjection` | `hp.GetCurrentMotorConfiguration(0)` → mutate → `hp.ProjectMotorConfiguration(config, 0)` (Rule 12) |
| Writing numeric params while UI language ≠ `en-US` | Decimal separator mismatch causes wrong values | Force `en-US` before write loop, restore after (Rule 7) |



## Related Files

- [`hardware-and-modules`](../hardware-and-modules/SKILL.md) — hardware module insertion, type changes, and hardware catalog
- [`parameters`](../parameters/SKILL.md) — parameter access and BiCo wiring through DriveObject.Parameters
- [`safety-commissioning`](../safety-commissioning/SKILL.md) — safety configuration via DriveFunctionInterface.SafetyCommissioning
- [`telegrams`](../telegrams/SKILL.md) — telegram management on DriveObject.Telegrams
- [`networks-and-drivecliq`](../networks-and-drivecliq/SKILL.md) — DriveCliq topology and network port management

---

## Online Drive Object Access

### 14. Navigate from `DriveObject` to its `DeviceItem` using `Parent<T>()`

`DriveObject` does not directly expose its parent `DeviceItem`. Use the generic `Parent<T>()` extension to walk up the object tree:

```csharp
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.MC.Drives;

DeviceItem deviceItem = driveObject.Parent<DeviceItem>();
```

This is the required first step before calling `GetService<OnlineDriveObjectContainer>()`.

---

### 15. Get the `OnlineDriveObject` from a `DriveObject`

**Description:** When the device is online, the live counterpart of an offline `DriveObject` is an `OnlineDriveObject`. Retrieve it via `GetService<OnlineDriveObjectContainer>()` on the parent `DeviceItem`, then match by `DriveObjectNumber`.

**Example:**

```csharp
DeviceItem deviceItem = driveObject.Parent<DeviceItem>();
if (deviceItem == null) return null;

var container = deviceItem.GetService<OnlineDriveObjectContainer>();
OnlineDriveObject onlineAxis = container?.OnlineDriveObjects
    .FirstOrDefault(o => o.DriveObjectNumber == driveObject.DriveObjectNumber);
```

**Key Types and Methods:**
- `OnlineDriveObjectContainer` — service on the drive's `DeviceItem`; returns `null` if the device is offline
- `OnlineDriveObjectContainer.OnlineDriveObjects` — collection of `OnlineDriveObject` instances
- `OnlineDriveObject.DriveObjectNumber` — matches the offline `DriveObject.DriveObjectNumber`
- `DriveObject.Parent<DeviceItem>()` — walks up the object tree to the owning `DeviceItem`

---

### 16. Read and write parameters via `OnlineDriveObject` (online mode)

**Description:** `OnlineDriveObject` exposes the same `Parameters` and `ReadParameters` compositions as `DriveObject`, but reads/writes go directly to the device's RAM — not the TIA project. Use `Parameters.Find(index, subindex)` to read/write, and `ReadParameters.Find(index, subindex)` for unrestricted read access (including r-parameters that bypass parameter whitelists).

**Example:**

```csharp
OnlineDriveObject onlineAxis = GetOnlineDriveObject(driveObject); // see Rule 15

// Read a parameter online
var param = onlineAxis.Parameters.Find(1460, 0);
var value = param?.Value;

// Read an r-parameter online (unrestricted read)
var rParam = onlineAxis.ReadParameters.Find(945, 0);
var rValue = rParam?.Value;

// Write a parameter online (goes to device RAM immediately)
onlineAxis.Parameters.Find(1460, 0).Value = 2.5f;
```

**Key Types and Methods:**
- `OnlineDriveObject.Parameters` — writable `DriveParameterComposition` for device RAM reads/writes
- `OnlineDriveObject.ReadParameters` — unrestricted read-only `ReadDriveParameterComposition`
- `DriveParameter.Find(index, subindex)` — same API as offline `DriveObject.Parameters`

**Note:** `Telegrams` are NOT available on `OnlineDriveObject`. Telegram configuration always uses the offline `DriveObject.Telegrams`.

---

### 17. Perform "Copy RAM to ROM" via `OnlineDriveFunctionInterface.DriveDomainFunctions`

**Description:** SINAMICS drives keep parameter changes in volatile RAM until explicitly saved to non-volatile ROM ("Copy RAM to ROM" / "Save parameters permanently" — the same action as the toolbar button in STARTER/Startdrive). There is no parameter-write-based trick for this (no need to write p0971/p0977 etc. directly) — Openness exposes it as a first-class method on `DriveDomainFunctions`, reached from an `OnlineDriveObject` via `GetService<OnlineDriveFunctionInterface>()`. This pattern is used in production by the mass-operations download tooling's "Save RAM to ROM after download" feature.

```csharp
using Siemens.Engineering.MC.Drives;
using Siemens.Engineering.MC.Drives.DFI;

// deviceItem = the DeviceItem whose DriveObjectContainer holds the drive object(s) (Rule 2)
// The device must already be online (see OnlineProvider.GoOnline — devices-and-hardware / online-and-download skills)
OnlineDriveObject onlineDriveObject = deviceItem
    .AsOnlineDriveObjectContainer()   // or GetService<OnlineDriveObjectContainer>()
    .OnlineDriveObjects.First();

OnlineDriveFunctionInterface onlineDfi = onlineDriveObject.GetService<OnlineDriveFunctionInterface>();
DriveDomainFunctions driveDomainFunctions = onlineDfi.DriveDomainFunctions;

bool success = driveDomainFunctions.PerformRAMtoROMCopyAllDriveObject();
```

**Key Types and Methods:**
- `Siemens.Engineering.MC.Drives.DFI.OnlineDriveFunctionInterface` — service retrieved via `OnlineDriveObject.GetService<OnlineDriveFunctionInterface>()`; exposes `.DriveDomainFunctions`
- `Siemens.Engineering.MC.Drives.DFI.DriveDomainFunctions` — exposes `PerformRAMtoROMCopyAllDriveObject()`
- `PerformRAMtoROMCopyAllDriveObject()` — returns `bool` (success); despite being callable from a single `OnlineDriveObject`, it saves **all** drive objects on that device/Control Unit to ROM, not just the one it was called on
- Any single `OnlineDriveObject` on the target device works as the entry point — you do not need to call this once per axis

**Anti-pattern:** Do not attempt this by writing a SINAMICS parameter such as `p0971`/`p0977` directly via `Parameters.Find(...)`. No such parameter-write path exists/is needed in current TIA Portal versions — `PerformRAMtoROMCopyAllDriveObject()` is the correct and only supported Openness entry point.

**Verification:** Confirm the API and method signature against the installed SDK
for the supported TIA Portal version before use. Exercise this operation only in
an isolated test environment because it persists the parameters of all drive
objects on the target device.
