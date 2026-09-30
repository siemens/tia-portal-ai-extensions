---
name: openness-base
description: Foundational knowledge for ALL TIA Portal Openness development. Covers SDK DLL discovery, TypeIdentifier requirements, and core development prerequisites. This skill should be loaded alongside any other Openness skill.
---

# Openness Base — Core Development Prerequisites

## Overview

This skill contains **shared foundational knowledge** required for **every** TIA Portal Openness application. Always load this skill alongside any other Openness skill to ensure critical context is never lost.

---

## Finding SDK DLLs via Registry

The Siemens Engineering SDK DLLs are **not in the GAC**. Their location depends on the installed TIA Portal version. Use the Windows registry to discover the installation path dynamically.

> ⚠️ **Never manually probe the filesystem for the TIA Portal installation or the SDK DLLs** (e.g. `Get-ChildItem`/`dir`/`Test-Path` scans of `Program Files`, `C:\Program Files\Siemens\...`, or recursive searches for `Siemens.Engineering*.dll`). This is slow, unreliable across machines, and unnecessary. **Always** resolve the install location via the registry lookup below — bake it directly into the `.csproj` with `MSBuild::GetRegistryValueFromView` so the project is portable across machines without any manual discovery step, before writing any other code.

### SDK-Style .csproj (Recommended)

Always use the **SDK-style project format** for new TIA Portal Openness applications. The target framework must be `net48`.

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TiaVersion>21</TiaVersion>
    <TiaPortalLocation>$([MSBuild]::GetRegistryValueFromView(`HKEY_LOCAL_MACHINE\SOFTWARE\Siemens\Automation\_InstalledSW\TIAP$(TiaVersion)\Global`, `Path`, '', RegistryView.Registry64, RegistryView.Registry32))</TiaPortalLocation>
  </PropertyGroup>

  <PropertyGroup>
    <TargetFramework>net48</TargetFramework>
    <LangVersion>latest</LangVersion>
    <ImplicitUsings>enable</ImplicitUsings>
    <OutputType>Exe</OutputType>
  </PropertyGroup>

  <ItemGroup>
    <Reference Include="Siemens.Engineering.Base">
      <HintPath>$(TiaPortalLocation)\PublicAPI\V$(TiaVersion)\net48\Siemens.Engineering.Base.dll</HintPath>
      <Private>False</Private>
      <SpecificVersion>False</SpecificVersion>
    </Reference>
    <Reference Include="Siemens.Engineering.Step7">
      <HintPath>$(TiaPortalLocation)\PublicAPI\V$(TiaVersion)\net48\Siemens.Engineering.Step7.dll</HintPath>
      <Private>False</Private>
      <SpecificVersion>False</SpecificVersion>
    </Reference>
    <Reference Include="Siemens.Engineering.Startdrive">
      <HintPath>$(TiaPortalLocation)\PublicAPI\V$(TiaVersion)\net48\Siemens.Engineering.Startdrive.dll</HintPath>
      <Private>False</Private>
      <SpecificVersion>False</SpecificVersion>
    </Reference>
  </ItemGroup>
</Project>
```

### Key Details

- **Registry key:** `HKEY_LOCAL_MACHINE\SOFTWARE\Siemens\Automation\_InstalledSW\TIAP$(TiaVersion)\Global`
- **Path value:** The `Path` value under this key contains the TIA Portal installation directory
- **DLL location:** `\PublicAPI\V$(TiaVersion)\net48\`
- **Registry views:** Check both `RegistryView.Registry64` and `RegistryView.Registry32` for compatibility
- **Common DLLs:** `Siemens.Engineering.Base`, `Siemens.Engineering.Step7`, `Siemens.Engineering.Startdrive`, `Siemens.Engineering.DCC`, `Siemens.Engineering.Safety`

---

## TypeIdentifier Requirements for Hardware

When creating or plugging hardware, the `TypeIdentifier` (order number with version) is **mandatory**. If the user does not provide it, **always ask for it** and guide them on how to find it.

### How to Find the TypeIdentifier

> Go to **Options → Settings → Hardware Configuration → Enable Display of the Type Identifier** in TIA Portal.
> After enabling, the `TypeIdentifier` appears in the hardware catalog module details.
> Example format: `OrderNumber:6SL3224-0BE32-0UA0/V2.9`

### TypeIdentifier Format

```
OrderNumber:<MLFB>
OrderNumber:<MLFB>//<version>
```

Where `<MLFB>` is the Siemens material number (e.g., `6SL3120-1TE15-0Axx`) and `<version>` is the firmware version (e.g., `10002`).

---

## Required Assembly Matrix

| Domain | Required DLLs |
|--------|------|
| Base / Session / Engineering Objects | `Siemens.Engineering.Base` |
| Step7 (PLC blocks, tags, devices) | `Siemens.Engineering.Base`, `Siemens.Engineering.Step7` |
| Startdrive (SINAMICS drives) | `Siemens.Engineering.Base`, `Siemens.Engineering.Step7`, `Siemens.Engineering.Startdrive` |
| DCC (Drive Control Charts) | `Siemens.Engineering.Base`, `Siemens.Engineering.DCC`, `Siemens.Engineering.Startdrive` |
| Safety | `Siemens.Engineering.Base`, `Siemens.Engineering.Step7`, `Siemens.Engineering.Safety` |

---

## 🛑 Namespaces Are NOT All `Siemens.Engineering` — Verified Namespace Map

Referencing `Siemens.Engineering.Base.dll` does **not** mean every type lives directly in the `Siemens.Engineering` namespace. Hardware/device/network types live in **sub-namespaces** within that same assembly. Using only `using Siemens.Engineering;` and guessing at types like `Device`, `DeviceItem`, or `NetworkInterface` produces `CS0246` ("type or namespace not found") build errors even though the assembly reference is correct and resolves fine.

**Confirmed namespaces (TIA Portal V21, `Siemens.Engineering.Base.dll`):**

| Type | Namespace |
|---|---|
| `TiaPortal`, `Project` | `Siemens.Engineering` |
| `Device`, `DeviceComposition`, `DeviceItem`, `DeviceItemClassifications` | `Siemens.Engineering.HW` |
| `Node`, `Subnet`, `IoSystem`, `IoController`, `IoConnector`, `NetType` | `Siemens.Engineering.HW` |
| `NetworkInterface`, `SoftwareContainer`, `NetworkPort` | `Siemens.Engineering.HW.Features` |

**Required `using` directives for hardware/device/network code:**

```csharp
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
```

**How to verify namespaces yourself for a type not listed above** (rather than guessing or trial-and-error compiling): use `ReflectionOnlyLoadFrom` from a `powershell.exe` (Windows PowerShell, not `pwsh`) process — `Assembly.GetTypes()` throws `ReflectionTypeLoadException` on this assembly because of unresolved dependent types, so catch it and read the exception's `Types` property (entries for unloadable types come back as `null` and must be filtered out):

```powershell
$asm = [System.Reflection.Assembly]::ReflectionOnlyLoadFrom('<TiaPortalLocation>\PublicAPI\V21\net48\Siemens.Engineering.Base.dll')
try {
    $types = $asm.GetTypes()
} catch [System.Reflection.ReflectionTypeLoadException] {
    $types = $_.Exception.Types | Where-Object { $_ -ne $null }
}
$types | Where-Object { $_.Name -eq 'TheTypeYouAreLookingFor' } | ForEach-Object { $_.FullName }
```

Do this check once per new type/domain the first time you touch it, and record the result back into the relevant skill file so subsequent sessions don't repeat the discovery step.

---

## Versioning and Compatibility

### Long-Term API Compatibility (LTS)

A TIA Portal version supports its matching Openness API version **plus three LTS (Long-Term Support) APIs** from previous versions. LTS APIs guarantee 100% binary, behavior, and source compatibility across TIA Portal versions, so an app built against an LTS API keeps working unmodified as TIA Portal is upgraded.

**Key points:**
- Pin an explicit API version for stable, long-lived integrations rather than always targeting the newest.
- There was a one-time restart of the LTS chain in V21 due to new security requirements; V21 onwards resumes the normal rolling LTS model.

### Modular Assemblies Since V21

Before TIA Portal V21, a single `Siemens.Engineering.dll` was generated per machine from the installed packages. Expecting a class from a package the customer never installed could throw a `TypeLoadException` at runtime. Since TIA Portal V21, each package ships its **own modular assembly**, removing that cross-installation risk.

**Key points:**
- On V21+, reference only the assemblies for the packages your app actually needs (see the Required Assembly Matrix above) — missing packages now fail predictably instead of with a generic `TypeLoadException`.
- Openness cannot open or access a project if mandatory or optional TIA Portal packages used by that project are missing:
  - **Opening** such a project throws `MissingProductsException` with a clear message identifying the missing product(s).
  - **Attaching** to such a project (already open in TIA Portal) throws no exception — instead, the project's and session's compositions are empty. Check for this explicitly rather than assuming a non-null project means a usable one.

## Quick Reference

| Topic | Details |
|-------|---------|
| **DLL location** | `$(TiaPortalLocation)\PublicAPI\V$(TiaVersion)\net48\` via registry — never filesystem probing |
| **TypeIdentifier** | Required for `PlugNew()` and `CreateWithItem()` — enable in Options |
| **Registry key** | `HKLM\SOFTWARE\Siemens\Automation\_InstalledSW\TIAP$(TiaVersion)\Global` |
| **Base namespace** | `Siemens.Engineering` |
| **LTS compatibility** | Current + 3 previous LTS API versions, 100% binary/behavior/source compatible |
| **Modular assemblies** | Since V21, one assembly per package — avoids `TypeLoadException` for missing packages |
| **`MissingProductsException`** | Thrown on open (not attach) when mandatory/optional packages are missing |

For live TIA Portal Openness integration-test implementation and CI guidance, see [`openness-testing`](../openness-testing/SKILL.md).

## Related Files

- [`engineering-objects`](../engineering-objects/SKILL.md) — general exception handling, including `MissingProductsException`
- [`session-and-project`](../session-and-project/SKILL.md) — the mandatory TIA Portal version check before coding, opening vs. attaching to projects
- [`licensing-and-firewall`](../licensing-and-firewall/SKILL.md) — product/option licensing distinct from package/assembly availability
- [`openness-testing`](../openness-testing/SKILL.md) — live TIA Portal Openness integration-test and CI guidance
