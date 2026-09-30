---
name: safety-commissioning
description: Safety commissioning for SINAMICS drives. Use when configuring PROFIsafe functions like STO and SImO, updating safety checksums, setting safety axis type, activating safety parameter bits, and managing acceptance tests.
metadata:
  siemens-depends-on: "openness-base, drive-objects, telegrams"
---

# Safety Commissioning

## Overview

Safety commissioning in SINAMICS drives configures PROFIsafe functions such as STO (Safe Torque Off), SImO (Safe Limited Operation), and other safety-related features. Access safety APIs through `DriveFunctionInterface.SafetyCommissioning` and `DriveFunctionInterface.FunctionInUse`. Activate safety functions by setting specific parameter bits (e.g., `p9601.3` for Basic Safety, `p9603.1` for PROFIsafe, `p9604.0` for STO). After parameter changes, update safety checksums via `UpdateCheckSums()`.

## Required Namespaces

```csharp
using System.Linq;
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

### SafetyCommissioning.UpdateCheckSums()

**Description:** Calculate and update safety checksums after safety parameter changes. This is mandatory after modifying any safety-related parameter to ensure the drive accepts the configuration.

**Example:**

```csharp
var succeeded = driveFunctionInterface.SafetyCommissioning.UpdateCheckSums();
```

**Key Types and Methods:**
- `SafetyCommissioning.UpdateCheckSums()` — recalculates all safety checksums
- Returns `bool` indicating success or failure

### FunctionInUse.SetSIAxisType

**Description:** Set the safety axis type (Rotary or Linear) via `FunctionInUse`. Required for safety functions that depend on axis kinematics (SImO, SLS, SMVO).

**Example:**

```csharp
var dfi = driveObject.GetService<DriveFunctionInterface>();
dfi.FunctionInUse.SetSIAxisType(RotaryLinearFlag.Linear);
```

**Key Types and Methods:**
- `FunctionInUse` — manages safety function activation state
- `SetSIAxisType(flag)` — sets the axis type for safety calculations
- `RotaryLinearFlag.Linear` / `RotaryLinearFlag.Rotary` — axis type enumeration

### Safety Parameter Bit Activation (STO via p9604)

**Description:** Enable safety functions (PROFIsafe, STO) by setting specific parameter bits. This is the standard activation pattern for SINAMICS S120 safety functions.

**Example:**

```csharp
parameters.Find("p9603").Bits
    .Single(x => x.Name == "p9603.1")
    .Value = 1;  // Enable PROFIsafe

parameters.Find("p9604").Bits
    .Single(x => x.Name == "p9604.0")
    .Value = 1;  // Enable STO
```

**Key Types and Methods:**
- `p9603.1` — PROFIsafe enable bit
- `p9604.0` — STO enable bit
- `Parameter.Bits[].Value` — bit-level write access

### Basic Safety PROFIsafe Activation (S120)

**Description:** Enable Basic Safety via `p9601.3` bit on SINAMICS S120. This is a prerequisite for other safety functions.

**Example:**

```csharp
var parameters = axis.GetService<DriveObjectContainer>()
    .DriveObjects.First().Parameters;

parameters.Find("p9601").Bits
    .Single(x => x.Name == "p9601.3")
    .Value = 1;
```

**Key Types and Methods:**
- `p9601.3` — Basic Safety enable bit (S120)
- Must be set before activating individual safety functions

### SafetyAcceptanceTestProvider

**Description:** Configure safety acceptance tests. The `SafetyAcceptanceTestProvider` exposes acceptance test parameters that must be confirmed before safety functions become active on the drive.

**Example:**

```csharp
var dfi = driveObject.GetService<DriveFunctionInterface>();
var acceptanceTest = dfi.SafetyCommissioning.SafetyAcceptanceTestProvider;
```

**Key Types and Methods:**
- `SafetyAcceptanceTestProvider` — manages safety acceptance test state
- Accessed via `SafetyCommissioning.SafetyAcceptanceTestProvider`

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `SafetyCommissioning.UpdateCheckSums()` | Recalculate safety checksums |
| `FunctionInUse.SetSIAxisType(flag)` | Set rotary/linear axis type |
| `p9601.3 = 1` | Enable Basic Safety (S120) |
| `p9603.1 = 1` | Enable PROFIsafe |
| `p9604.0 = 1` | Enable STO |
| `SafetyAcceptanceTestProvider` | Configure safety acceptance tests |

## Related Files

- [`drive-objects`](../drive-objects/SKILL.md) — obtaining `DriveFunctionInterface` to access safety APIs
- [`parameters`](../parameters/SKILL.md) — parameter bit access pattern used for safety activation
- [`telegrams`](../telegrams/SKILL.md) — safety telegram insertion (`InsertSafetyTelegram`) is required for PROFIsafe
- [`networks-and-drivecliq`](../networks-and-drivecliq/SKILL.md) — PROFINET configuration for safety data exchange

## Exception Handling

- `UpdateCheckSums()` returns `false` if the safety configuration is invalid. Check the return value and inspect safety parameters.
- Safety parameter writes require the drive to be in an appropriate state. Writing while online may throw `EngineeringException`.
- `SetSIAxisType()` may fail if safety functions are already active. Deactivate the drive before changing axis type.
- Always set `p9601.3` (Basic Safety) **before** enabling individual safety functions (`p9603.1`, `p9604.0`). The order matters.
- `SafetyAcceptanceTestProvider` operations may require additional validation. Check the provider state before modifying acceptance tests.
