---
name: parameters
description: Drive parameters for SINAMICS drives. Use when reading/writing parameters, BiCo wiring, accessing parameters by index or name, and manipulating parameter bits.
metadata:
  siemens-depends-on: "openness-base, drive-objects"
---

# Parameters

## Overview

Drive parameters in SINAMICS drives are accessed through the `Parameters` collection on a `DriveObject`. Parameters can be retrieved by numeric index, by string name (e.g., `"r945[2]"`), or via `Find(index, subindex)` for BiCo wiring. Parameter bits provide granular control, enabling individual bit toggling for safety activation and feature flags.

## Required Namespaces

```csharp
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.MC.Drives;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`
- `Siemens.Engineering.Startdrive.dll`

## Common Patterns

### BiCo Parameter Wiring

**Description:** Find a BiCo parameter by index and subindex, locate a target parameter bit, and assign the bit as the BiCo value. This creates a cross-wiring connection between parameters.

**Example:**

```csharp
var bicoParameter = redAxis.GetService<DriveObjectContainer>()
    .DriveObjects.First()
    .Parameters.Find(840, 0);

var connectedParameter = parameterBits.First(
    x => x.Name.Substring(x.Name.IndexOf('.') + 1) == "7");

bicoParameter.Value = connectedParameter;
```

**Key Types and Methods:**
- `Parameters.Find(index, subindex)` — locate a BiCo-capable parameter by numeric address
- `Parameter.Value` — assign a `ParameterBit` reference as the BiCo source
- `ParameterBits` — collection of available bit references for wiring

### Read Parameter Value

**Description:** Read the current value of a drive parameter by accessing its `.Value` property. This is the most common parameter operation — retrieving the current setting of a parameter like `r945` (motor rated current) or any other read/writable parameter.

**Example:**

```csharp
var parameter = driveObject.Parameters.Find("r945[2]");
if (parameter != null)
{
    var currentValue = parameter.Value;
    Console.WriteLine($"Parameter {parameter.Name} = {currentValue}");
}
```

**Key Types and Methods:**
- `Parameter.Value` — get the current value of the parameter
- `Parameter.Name` — the SINAMICS parameter name (e.g., `"r945[2]"`)

### Parameter Access by Index

**Description:** Access a drive parameter via numeric index from the `Parameters` collection. Direct index access is the fastest way to retrieve a known parameter.

**Example:**

```csharp
var parameters = driveObject.Parameters;
var parameterViaIndexAccess = parameters[100];
```

**Key Types and Methods:**
- `Parameters[index]` — indexer to retrieve a parameter by numeric ID
- `Parameter` — the returned parameter object with `.Value`, `.Name`, `.Bits`

### Parameter Access by String Name

**Description:** Find a parameter using `Parameters.Find(string)` with the parameter name, e.g., `"r945[2]"` for read-only parameters or `"p999"` for writable ones.

**Example:**

```csharp
var parameterViaStringAccess = parameters.Find("r945[2]");
```

**Key Types and Methods:**
- `Parameters.Find(name)` — locate parameter by SINAMICS naming convention
- Read parameters use `"r"` prefix; write parameters use `"p"` prefix

### Parameter Bit Access by Name

**Description:** Access a specific bit of a parameter via the `.Bits` collection and filter by the fully qualified bit name (e.g., `"p9603.1"`). Setting bit values enables individual features like safety functions.

**Example:**

```csharp
parameters.Find("p9603").Bits
    .Single(x => x.Name == "p9603.1")
    .Value = 1;
```

**Key Types and Methods:**
- `Parameter.Bits` — collection of individual bits within a parameter
- `Bit.Name` — fully qualified name in `"parameter.bit"` format
- `Bit.Value` — set or read the bit value (0 or 1)

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `Parameter.Value` (read) | Read the current value of a parameter |
| `Parameters.Find(index, subindex)` | Locate BiCo parameter by numeric address |
| `Parameters[index]` | Direct index access to a parameter |
| `Parameters.Find("r945[2]")` | Find parameter by string name |
| `Parameter.Bits.Single(x => x.Name == "p9603.1").Value` | Access and set individual parameter bits |
| `Parameter.Value = bit` | Assign a BiCo wiring connection |

## Related Files

- [`drive-objects`](../drive-objects/SKILL.md) — obtaining the `DriveObject` whose `Parameters` collection you access
- [`safety-commissioning`](../safety-commissioning/SKILL.md) — uses parameter bit writes (e.g., `p9603`, `p9604`) to activate safety functions
- [`telegrams`](../telegrams/SKILL.md) — telegram configuration interacts with parameter-based addressing
- [`hardware-and-modules`](../hardware-and-modules/SKILL.md) — hardware projection sets configuration entries that map to parameters

## Exception Handling

- `Parameters.Find(string)` returns `null` if the parameter name does not exist. Always check for null before accessing properties.
- `Parameters[index]` throws `IndexOutOfRangeException` for invalid parameter numbers.
- `Parameter.Bits.Single()` throws `InvalidOperationException` if the bit name is not found. Use `FirstOrDefault()` with null checks for robust code.
- Writing to read-only parameters (e.g., `"r..."` prefix) throws `EngineeringException`. Only `"p..."` parameters are writable.
- BiCo wiring requires both source and target to support BiCo. Verify BiCo capability before assignment.
