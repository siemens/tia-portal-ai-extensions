---
name: security
description: UMAC security configuration in TIA Portal. Use when creating custom roles, project users, assigning device function rights, managing master passwords, checking project protection status, or configuring CPU protection/access-control level (PlcAccessControlConfiguration, PlcProtectionAccessLevel).
metadata:
  siemens-depends-on: "openness-base, engineering-objects, devices-and-hardware"
---

# Security

## Overview

Security in TIA Portal encompasses UMAC (Unified Machine Access Control) roles and permissions, PLC master passwords, and engineering function rights. The `UmacConfigurator` service manages custom roles, project users, and device-level access control. The `PlcMasterSecretConfigurator` service handles the CPU master password. Engineering function rights indicate whether the project itself is protected, restricting modification capabilities.

> **Note:** This skill covers **project-internal** security (who can do what *inside* a project). For **application-level** access control — whether your Openness app is allowed to connect to TIA Portal at all, the Openness firewall, and product licensing — see [`licensing-and-firewall`](../licensing-and-firewall/SKILL.md).

## Required Namespaces

```csharp
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.Umac;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`

## Common Patterns

### Create UMAC Custom Role and Assign Device Function Rights

**Description:** Create a custom UMAC role and grant it specific device function rights. The `UmacConfigurator` manages custom roles, while `UmacDevice` exposes the available rights for a particular device.

**Example:**

```csharp
var umacConfigurator = Project.GetService<UmacConfigurator>();
var adminRole = umacConfigurator.CustomRoles.Create("Admin", "Description");
var umacDevice = device.GetService<UmacDevice>();
var rights = umacDevice.AvailableDeviceFunctionRights;
adminRole.AssignDeviceFunctionRight(umacDevice, rights.First());
```

**Key Types and Methods:**
- `UmacConfigurator` — service for UMAC security configuration
- `UmacConfigurator.CustomRoles` — collection of custom roles
- `CustomRole.Create(string, string)` — creates a new custom role
- `UmacDevice` — device-level UMAC security object
- `UmacDevice.AvailableDeviceFunctionRights` — rights available for the device
- `CustomRole.AssignDeviceFunctionRight()` — grants a right to a role

### Create UMAC Project User

**Description:** Create a project-level user account with a username and password. Project users authenticate against the project's UMAC system.

**Example:**

```csharp
umacConfigurator.ProjectUsers.Create("Admin", GetSecureString("AdminAdmin123"));
```

**Key Types and Methods:**
- `UmacConfigurator.ProjectUsers` — collection of project users
- `ProjectUser.Create(string, SecureString)` — creates a new project user

### Check Project Protection (Engineering Function Rights)

**Description:** Determine whether the project has engineering-level protection enabled by checking for active engineering function rights. A non-empty collection indicates the project is protected.

**Example:**

```csharp
var engineeringFunctionRights = umacConfigurator.EngineeringFunctionRights;
if (engineeringFunctionRights.Any())
{
    // Project is protected
}
```

**Key Types and Methods:**
- `UmacConfigurator.EngineeringFunctionRights` — collection of active engineering rights restrictions

### Set PLC Master Password

**Description:** Configure the CPU master password using the `PlcMasterSecretConfigurator` service. This password is required for certain online operations and downloads.

**Example:**

```csharp
var masterSecretConfigurator = cpu.GetService<PlcMasterSecretConfigurator>();
masterSecretConfigurator.Protect(secureString);
```

**Key Types and Methods:**
- `PlcMasterSecretConfigurator` — service for managing the PLC master password
- `PlcMasterSecretConfigurator.Protect(SecureString)` — sets the master password

### ⚠️ CPU protection & access-control settings (`PlcAccessControlConfiguration` / `PlcProtectionAccessLevel`)

**Description:** The "Protection & Security" settings visible on a CPU in the TIA Portal GUI (Access level, "Connection mechanisms", central/local user management) are configured through `Siemens.Engineering.HW.Features` services on the CPU's `DeviceItem` — **not** through `UmacConfigurator`/`UmacDevice` (those are project-level UMAC roles/rights, a different system). These services are discoverable primarily via assembly reflection over `Siemens.Engineering.HW.dll`/`Siemens.Engineering.HW.Features`; confirmed types and enum values from hands-on use:

```csharp
using Siemens.Engineering.HW.Features;

// Access-control configuration (which mechanism governs CPU protection)
var accessControlProvider = cpu.GetService<PlcAccessControlConfigurationProvider>();
PlcAccessControlConfiguration accessControlConfig = accessControlProvider.Configuration;
// Enum values observed: Disabled, EnabledWithAccessControl, ...ViaAccessLevel, ...AndCentralUser variants
// (exact member names are TIA-version-specific — enumerate the enum type at runtime to confirm on your installation)

// Access-level configuration (None/FullAccess/ReadAccess/HMIAccess/NoAccess/FullAccessIncludingFailsafe)
var accessLevelProvider = cpu.GetService<PlcAccessLevelProvider>();
PlcProtectionAccessLevel level = accessLevelProvider.PlcProtectionAccessLevel;
```

**Confirmed gotcha:** `PlcAccessLevelProvider.PlcProtectionAccessLevel` throws a `NullReferenceException` when read on a device that has **no password set yet** — check whether a password/protection scheme is configured before reading this property, and wrap the read in a try/catch as a fallback.

**Still open / not fully confirmed:** the exact attribute or service that maps to the specific "Protect confidential PLC configuration data" checkbox (distinct from the general access-level setting) has not been conclusively identified as of this writing. If you need this specific setting, budget time for `GetServiceInfos()`/`GetAttributeInfos()` probing on the CPU `DeviceItem` and its `HW.Features` services (see [`object-tree-walking`](../object-tree-walking/SKILL.md) and [`engineering-objects`](../engineering-objects/SKILL.md) for the enumeration pattern), and update this section once confirmed.

**Key Types and Methods:**
- `PlcAccessControlConfigurationProvider` — service on the CPU `DeviceItem`; exposes `PlcAccessControlConfiguration`
- `PlcAccessLevelProvider` — service on the CPU `DeviceItem`; exposes `PlcProtectionAccessLevel`
- `PlcAccessControlConfiguration` (enum) — access-control mechanism (disabled / access-control / central-user variants)
- `PlcProtectionAccessLevel` (enum) — `None`, `FullAccess`, `ReadAccess`, `HMIAccess`, `NoAccess`, `FullAccessIncludingFailsafe`

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `UmacConfigurator.CustomRoles.Create()` | Create a custom UMAC role |
| `UmacDevice.AvailableDeviceFunctionRights` | List rights assignable to a device |
| `CustomRole.AssignDeviceFunctionRight()` | Grant a device function right to a role |
| `UmacConfigurator.ProjectUsers.Create()` | Create a project user account |
| `UmacConfigurator.EngineeringFunctionRights` | Check if project is protected |
| `PlcMasterSecretConfigurator.Protect()` | Set the CPU master password |
| `cpu.GetService<PlcAccessControlConfigurationProvider>()` | Read/configure CPU access-control mechanism |
| `cpu.GetService<PlcAccessLevelProvider>().PlcProtectionAccessLevel` | Read/configure the CPU access level |

## Related Files

- [`online-and-download`](../online-and-download/SKILL.md) — master password may be required for downloads
- [`blocks`](../blocks/SKILL.md) — blocks can be individually password-protected
- [`devices-and-hardware`](../devices-and-hardware/SKILL.md) — UMAC device rights are per-device

## Exception Handling

- `EngineeringException` is thrown if the UMAC configuration is locked or if the project is already protected with conflicting rights
- `ArgumentException` may be thrown if the password does not meet complexity requirements (check `GetInvalidPasswordCharacters()` before setting)
- `InvalidOperationException` occurs when attempting to modify engineering function rights on a project that is already protected
- Always verify `EngineeringFunctionRights.Any()` before assuming the project is unprotected
- `PlcAccessLevelProvider.PlcProtectionAccessLevel` throws `NullReferenceException` when read on a CPU with no password/protection configured yet — guard with a try/catch or a prior existence check
