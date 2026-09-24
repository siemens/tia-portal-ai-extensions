---
name: engineering-objects
description: Working with engineering objects in TIA Portal Openness. Use when managing exclusive access, transactions, attribute read/write, GetService patterns, hardware catalog searches, navigating the object tree, or stamping custom identities via CustomIdentityProvider.
metadata:
  siemens-depends-on: "openness-base, session-and-project, performance-and-caching, threading-and-concurrency"
---

# Engineering Objects

## Overview

This skill covers patterns for working with engineering objects in TIA Portal using the Siemens Engineering SDK. It includes acquiring exclusive access, creating transactions, navigating the object tree, reading/writing attributes, and resolving SDK assemblies dynamically.

Engineering objects represent everything inside a TIA Portal project — devices, PLCs, networks, software, and more. All modifications must occur within an `ExclusiveAccess` block.

## Required Namespaces

```csharp
using Siemens.Engineering;
using Siemens.Engineering.CustomIdentity;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.HardwareCatalog;
using System;
using System.IO;
using System.Linq;
using Microsoft.Win32;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`

---

### Find SDK DLLs via Registry (MSBuild)

**Description:** The TIA Portal Openness SDK DLLs are not in the GAC. For creating Openness applications, locate the DLLs dynamically via the Windows registry in your `.csproj` file:

**SDK-Style .csproj Example:**
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
  </ItemGroup>
</Project>
```

**Key Details:**
- Registry key: `HKEY_LOCAL_MACHINE\SOFTWARE\Siemens\Automation\_InstalledSW\TIAP$(TiaVersion)\Global`
- The `Path` value gives the TIA Portal installation directory
- DLLs live under `\PublicAPI\V$(TiaVersion)\net48\`
- Check both `RegistryView.Registry64` and `RegistryView.Registry32` for compatibility

## Common Patterns

### Acquire Exclusive Access

**Description:** Obtains an exclusive lock on the TIA Portal session, which is required before performing any engineering operations. The `ExclusiveAccess` object implements `IDisposable` and should be used in a `using` statement. The text parameter provides status feedback displayed in the TIA Portal UI.

**Example:**
```csharp
using var exclusiveAccess = TiaPortalInstance.ExclusiveAccess("Test");
exclusiveAccess.Text = "Start of the program";
// ... engineering operations ...
exclusiveAccess.Text = "End of the program";
```

**Key Types and Methods:**
- `TiaPortal.ExclusiveAccess(string)` — acquires the exclusive lock; the string identifies the automation client
- `ExclusiveAccess` — represents the exclusive session; implements `IDisposable`
- `ExclusiveAccess.Text` — sets status text shown in the TIA Portal UI

---

### Create Transaction Within Exclusive Access

**Description:** Creates a transaction scope inside an exclusive access block. Transactions group multiple operations so they can be committed or rolled back atomically. Always create transactions within an existing `ExclusiveAccess`.

**Example:**
```csharp
using var exclusiveAccess = TiaPortalInstance.ExclusiveAccess("Test");
using var transaction = exclusiveAccess.Transaction(Project, "Test");
// ... engineering operations ...
transaction.CommitOnDispose();
```

**Key Types and Methods:**
- `ExclusiveAccess.Transaction(Project, string)` — creates a new transaction tied to the project
- `Transaction.CommitOnDispose()` — ensures all changes are committed when the transaction is disposed

---

### Access Project Name

**Description:** Reads the `Name` property of a project to identify or filter it. Commonly used when iterating over open projects to find a specific one.

**Example:**
```csharp
foreach (var project in TiaPortalInstance.Projects)
{
    if (project.Name != expectedName) continue;
    Project = project;
    return;
}
```

**Key Types and Methods:**
- `Project.Name` — returns the project name as a string

---

### Dynamic Assembly Resolution via Registry

**Description:** Resolves Siemens Engineering SDK assemblies at runtime by querying the Windows registry. This is necessary because TIA Portal installs versioned assemblies that are not in the GAC, and the SDK assembly versions change between TIA Portal releases.

**Example:**
```csharp
public static Assembly ResolveSiemensEngineeringAssembly(object sender, ResolveEventArgs args)
{
    var assemblyName = new AssemblyName(args.Name);
    if (assemblyName.Name != "Siemens.Engineering.Base")
        return null;
    var assemblyVersion = args.Name.Split(',').FirstOrDefault(x => x.Contains("Version")).Split('=')[1].Split('.')[0];
    using var regBaseKey = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64);
    using var opennessBaseKey = regBaseKey.OpenSubKey(@"SOFTWARE\Siemens\Automation\Openness");
    using var registryKeyLatestTiaVersion = opennessBaseKey?.OpenSubKey(
        opennessBaseKey.GetSubKeyNames().FirstOrDefault(x => x.Contains(assemblyVersion)));
    using var assemblyVersionSubKey = registryKeyLatestTiaVersion
        ?.OpenSubKey("PublicAPI")?.OpenSubKey(assemblyName.Version.ToString())?.OpenSubKey("net48");
    var siemensEngineeringAssemblyPath = assemblyVersionSubKey?.GetValue("Siemens.Engineering.Base").ToString();
    return Assembly.LoadFrom(siemensEngineeringAssemblyPath);
}
```

**Key Types and Methods:**
- `Assembly.LoadFrom(string)` — loads an assembly from its file path
- `RegistryKey` — provides access to the Windows registry
- `ResolveEventArgs` — contains information about the unresolved assembly

---

### Register Assembly Resolve Handler

**Description:** Registers a callback handler for the `AssemblyResolve` event. When the runtime cannot find a required assembly, this handler is invoked to locate and load it dynamically.

**Example:**
```csharp
AppDomain.CurrentDomain.AssemblyResolve += OpennessAssemblyResolverSnippet.ResolveSiemensEngineeringAssembly;
```

**Key Types and Methods:**
- `AppDomain.CurrentDomain.AssemblyResolve` — event triggered when assembly resolution fails

---

### GetService\<T\> Pattern

**Description:** Retrieves a typed service from an engineering object that implements `IEngineeringServiceProvider`. Services provide specialized functionality (e.g., software containers, online capabilities, networking) associated with a device or CPU.

**Example:**
```csharp
var softwareContainer = cpu.GetService<SoftwareContainer>();
var onlineProvider = cpu.GetService<OnlineProvider>();
var downloadProvider = cpu.GetService<DownloadProvider>();
var networkInterface = deviceItem.GetService<NetworkInterface>();
```

**Key Types and Methods:**
- `IEngineeringServiceProvider.GetService<T>()` — retrieves a service of type `T` from the engineering object
- `SoftwareContainer` — service for managing PLC software
- `OnlineProvider` — service for online operations
- `DownloadProvider` — service for downloading to devices
- `NetworkInterface` — service for network configuration

---

### Classification Checks

**Description:** Filters engineering objects by their classification type. The `Classification` property identifies the role of a device item (e.g., CPU, I/O module, interface module).

**Example:**
```csharp
var cpu = device.DeviceItems.Single(x => x.Classification == DeviceItemClassifications.CPU);
```

**Key Types and Methods:**
- `DeviceItem.Classification` — returns the classification of the device item
- `DeviceItemClassifications.CPU` — constant for CPU classification

---

### Attribute Read/Write

**Description:** Reads and writes attributes on engineering objects. Attributes expose configurable properties (e.g., process image settings, safety block names). Use `GetAttributeInfos()` to discover available attributes, `GetAttribute()` to read values, and `SetAttribute()` to write values.

**Example:**
```csharp
// Read attributes
var profinetInterfaces = cpu.DeviceItems
    .Where(d => d.GetAttributeInfos().Select(x => x.Name).Contains("PnSendClock")).ToList();
var mainSafetyBlockName = runtimeGroup.GetAttribute("MainSafetyBlockName");

// Write attributes
address.SetAttribute("ProcessImage", Convert.ToInt32(processImagePartNumber));
```

**Key Types and Methods:**
- `IEngineeringObject.GetAttribute(string)` — reads the value of an attribute by name
- `IEngineeringObject.SetAttribute(string, object)` — writes a value to an attribute
- `IEngineeringObject.GetAttributeInfos()` — returns metadata about available attributes

---

### Hardware Catalog Search

**Description:** Searches the TIA Portal hardware catalog for entries matching a search string. Use this to find hardware components by their article number (e.g., "6ES7...") before inserting them into a project.

**Example:**
```csharp
var catalogEntry = TiaPortalInstance.HardwareCatalog.Find("6ES7");
```

**Key Types and Methods:**
- `TiaPortal.HardwareCatalog` — provides access to the hardware catalog
- `HardwareCatalog.Find(string)` — searches the catalog and returns matching `CatalogEntry` objects
- `CatalogEntry` — represents a hardware catalog entry

---

### Engineering Object Navigation

**Description:** Navigates the engineering object hierarchy. Move downward through collections (e.g., `Device.DeviceItems`, `SoftwareContainer.Software`) and upward via the `Parent` property.

**Example:**
```csharp
// Navigate down the tree
var software = device.DeviceItems.First(...).GetService<SoftwareContainer>().Software as PlcSoftware;
var chartContainer = driveObject.GetService<DriveControlChartContainer>();
var charts = chartContainer.Charts;

// Navigate up the tree
var parent = deviceItem.Parent;
```

**Key Types and Methods:**
- `Device.DeviceItems` — collection of items under a device
- `DeviceItem.Parent` — reference to the parent engineering object
- `IEngineeringComposition` — interface for objects that contain child collections

---

### Enumerate All Services Dynamically — `GetServiceInfos()`

**Description:** `GetServiceInfos()` is an **explicit interface implementation** on `IEngineeringServiceProvider`. It is not accessible on the concrete proxy type or via reflection — you must cast to the interface first. Use it to discover all services available on a given object at runtime, then retrieve each via the non-generic `IServiceProvider.GetService(Type)`.

**Example:**
```csharp
// Correct — cast to the interface before calling
if (obj is IEngineeringServiceProvider provider)
{
    IList<EngineeringServiceInfo> infos = provider.GetServiceInfos();
    foreach (EngineeringServiceInfo info in infos)
    {
        // Use non-generic IServiceProvider (not IEngineeringServiceProvider) for dynamic GetService
        object? svc = ((System.IServiceProvider)provider).GetService(info.Type);
        if (svc is IEngineeringObject svcObj)
        {
            // info.Type — the service's CLR type
            // svcObj    — the service instance
        }
    }
}

// Wrong — returns null; GetServiceInfos is an explicit interface impl, invisible on the proxy type
obj.GetType().GetMethod("GetServiceInfos")?.Invoke(obj, null); // null
```

**Ordering rule:** call `GetServiceInfos()` **before** any `GetService<T>()` call on the same object during a full traversal. `GetServiceInfos()` may register internal descriptors server-side that `GetService<T>()` requires. Skipping it can cause `GetService<T>()` to silently return `null` and makes the traversal an invalid repro for crash investigations (see [`crash-diagnosis`](../crash-diagnosis/SKILL.md)).

**Key Types and Methods:**
- `IEngineeringServiceProvider.GetServiceInfos()` — explicit interface impl; returns `IList<EngineeringServiceInfo>` (runtime-dynamic per device family)
- `EngineeringServiceInfo.Type` — the CLR `System.Type` of the service
- `System.IServiceProvider.GetService(Type)` — non-generic dynamic service retrieval

---

### Proxy Identity Equality — `Equals()` Not `==`

**Description:** The same underlying COM object can be wrapped in multiple distinct .NET proxy instances during an Openness session. The `==` operator compares .NET reference identity of the wrappers, not the underlying COM objects. `IEngineeringObject` overrides `Equals()` to compare underlying COM identity, so `HashSet<IEngineeringObject>` with default equality works correctly for deduplication.

**Example:**
```csharp
// Correct — Equals() compares underlying COM identity
var visited = new HashSet<IEngineeringObject>(); // uses overridden Equals/GetHashCode
if (!visited.Add(obj))
    return; // already visited this COM object

// Wrong — may miss already-visited objects when the same COM object
// is reached via a different proxy instance
if (proxy1 == proxy2) // false even if both wrap the same COM object
```

**Key Types and Methods:**
- `IEngineeringObject.Equals(object)` — overridden for COM identity comparison; safe for `HashSet<IEngineeringObject>`

---

### Stamping a Custom Identity — `CustomIdentityProvider`

**Description:** Any `IEngineeringObject` that implements `IEngineeringServiceProvider` may expose a `CustomIdentityProvider` service. This lets external tools attach a stable, tool-defined identity key/value pair to a TIA Portal object that survives renaming. The service is optional — not every object supports it — so a null check is mandatory.

**Example:**
```csharp
var serviceProvider = engineeringObject as IEngineeringServiceProvider;
var identityProvider = serviceProvider?.GetService<CustomIdentityProvider>();
if (identityProvider != null)
    identityProvider.Set("MyTool:ID", guidOrKeyString);
```

**Key rules:**
- `CustomIdentityProvider` lives in `Siemens.Engineering.CustomIdentity`.
- Cast to `IEngineeringServiceProvider` before calling `GetService<CustomIdentityProvider>()` — `IEngineeringObject` alone does not expose `GetService<T>()`.
- `GetService<CustomIdentityProvider>()` returns `null` when the object does not support custom identities — always null-check before calling `Set`.
- Apply identities in a **post-creation sweep** over all generated objects rather than inline during element creation, to ensure all objects exist before identity stamping begins.
- The identity key is caller-defined (e.g. `"MyTool:ID"`); the value is any string (typically a GUID).

**Key Types and Methods:**
- `CustomIdentityProvider` — service in `Siemens.Engineering.CustomIdentity`
- `CustomIdentityProvider.Set(string key, string value)` — attaches the identity pair to the object

## Quick Reference

| Method / Pattern | Purpose |
|---|---|
| `TiaPortal.ExclusiveAccess(string)` | Acquire exclusive lock for engineering operations |
| `ExclusiveAccess.Transaction(Project, string)` | Create a transaction within exclusive access |
| `Transaction.CommitOnDispose()` | Commit all changes when disposing the transaction |
| `Project.Name` | Read the project name |
| `TiaPortal.HardwareCatalog.Find(string)` | Search hardware catalog by article number |
| `IEngineeringServiceProvider.GetService<T>()` | Retrieve a typed service from an engineering object |
| `DeviceItem.Classification` | Check the classification of a device item |
| `IEngineeringObject.GetAttribute(string)` | Read an attribute value |
| `IEngineeringObject.SetAttribute(string, object)` | Write an attribute value |
| `IEngineeringObject.GetAttributeInfos()` | Discover available attributes |
| `Device.DeviceItems` | Navigate to child device items |
| `DeviceItem.Parent` | Navigate to the parent object |
| `AppDomain.CurrentDomain.AssemblyResolve` | Register dynamic assembly resolution handler |
| `((IEngineeringServiceProvider)obj).GetServiceInfos()` | Enumerate all services on an object (explicit interface cast required) |
| `((System.IServiceProvider)provider).GetService(type)` | Retrieve a service by `Type` dynamically after `GetServiceInfos()` |
| `obj.Equals(other)` (not `==`) | Compare COM proxy identity for deduplication |
| `(obj as IEngineeringServiceProvider)?.GetService<CustomIdentityProvider>()` | Get custom identity stamper (null if unsupported) |
| `identityProvider.Set(key, value)` | Stamp a stable identity string onto an engineering object |

## TIA Portal Openness Documentation Access

The official documentation at `https://docs.tia.siemens.cloud/r/en-us/v21/tia-portal-openness-api-for-automation-of-engineering-workflows` is a **JavaScript SPA (FluidTopics platform)** and cannot be read directly. Use the FluidTopics REST API instead.

### Key Identifiers

| Item | Value |
|---|---|
| **Base URL** | `https://docs.tia.siemens.cloud` |
| **Map ID (V21, en-US)** | `gpR5ZkKnLSuzVoGX1ovoKg` |

### API Endpoints

```
# Get full table of contents (all chapter titles + contentIds)
GET https://docs.tia.siemens.cloud/api/khub/maps/gpR5ZkKnLSuzVoGX1ovoKg/toc

# Read content of a specific page by contentId
GET https://docs.tia.siemens.cloud/api/khub/maps/gpR5ZkKnLSuzVoGX1ovoKg/topics/{contentId}/content

# List all available maps (find other versions/languages)
GET https://docs.tia.siemens.cloud/api/khub/maps?locale=en-US
```

### How to Find a Topic and Read It

**Step 1 — Find the contentId** from the TOC using PowerShell:
```powershell
$toc = curl -s "https://docs.tia.siemens.cloud/api/khub/maps/gpR5ZkKnLSuzVoGX1ovoKg/toc" | ConvertFrom-Json
function Get-Titles($node, $depth=0) {
    $indent = "  " * $depth
    Write-Host "$indent- $($node.title) [contentId: $($node.contentId)]"
    if ($node.children) { foreach ($child in $node.children) { Get-Titles $child ($depth+1) } }
}
Get-Titles $toc
```

**Step 2 — Fetch the page content** using `web_fetch`:
```
https://docs.tia.siemens.cloud/api/khub/maps/gpR5ZkKnLSuzVoGX1ovoKg/topics/{contentId}/content
```

### Key contentIds (V21, en-US)

| Topic | contentId |
|---|---|
| Root / Overview | `QaJz2AlV7QFrZCe4DSDmGA` |
| What's New in V21 | `rajAJWIJSS9m84qRksoNrg` |
| Requirements for TIA Openness | `sFlotaF06bTvAIslvMyVUg` |
| Object Model | `2nTegtIrIPOhtha_t5HM0A` |
| Creating a Device | `p6Q3_7fctGxlESjXPyc8ug` |
| Enumerating Devices | `pgOxSsdSpjur~HUNZ9tyUw` |
| Creating a Device Item | `Sp~9fjJzgmSNT1fop~AogQ` |
| Opening a Project | `kIIbtqJMFA1xic_l0jAv3Q` |
| Connecting to TIA Portal | `DP7NDA58oox~t1~oZJkHQQ` |
| Accessing Global Libraries | `oeM75FetZmhKg4oBdpwU6g` |
| Downloading to PLC | `qjiyVrLduKIDJsH_ev4AMg` |
| Blocks (overview) | `e4g2ullj_vd8lprBjZvgqQ` |
| Tags and Tag Tables | `4CPtjF8RIhah7uExdqfm9Q` |
| Handling Exceptions | `cGOasigCD_yUbQJLLGLJlQ` |
| Export/Import Overview | `jvppEtulvHQl3WSvUESL_w` |
| Major Changes V21 | `rajAJWIJSS9m84qRksoNrg` |

> When a user asks about a specific API feature not already covered in skills, look it up via the API above rather than guessing.

## Related Files

- [`session-and-project`](../session-and-project/SKILL.md) — patterns for session and project lifecycle management
- [`object-tree-walking`](../object-tree-walking/SKILL.md) — schema-free traversal, cycle prevention, service enumeration, proxy deduplication
- [`crash-diagnosis`](../crash-diagnosis/SKILL.md) — diagnosing hard TIA Portal crashes; breadcrumb patterns; why `GetServiceInfos()` ordering matters
- [`threading-and-concurrency`](../threading-and-concurrency/SKILL.md) — thread-affinity rules for proxy objects and the `TiaPortal` instance
- [`licensing-and-firewall`](../licensing-and-firewall/SKILL.md) — `LicenseNotFoundException` and `EngineeringSecurityException` (Openness firewall)
- [`openness-base`](../openness-base/SKILL.md) — versioning/compatibility, including `MissingProductsException` on project open

## Exception Handling

- **Exclusive Access Timeout:** If another automation client holds the exclusive lock, `ExclusiveAccess()` will throw. Ensure no other client is active or handle the timeout gracefully.
- **Transaction Rollback:** If an operation fails within a transaction block, do not call `CommitOnDispose()`. The transaction will roll back automatically on disposal, undoing all changes.
- **Service Not Available:** `GetService<T>()` throws if the requested service is not supported by the engineering object. Check object classification or capabilities before requesting services.
- **Attribute Not Found:** `GetAttribute()` and `SetAttribute()` throw if the attribute name does not exist. Use `GetAttributeInfos()` to verify available attributes first.
- **Hardware Catalog Empty:** `HardwareCatalog.Find()` may return no results if the search string does not match any catalog entries or if the catalog is not yet loaded.
- **Disposed or Stale Proxy:** Touching a deleted object or a proxy that has become stale (e.g. after `Import()` replaced its target, see [`global-library`](../global-library/SKILL.md)) throws `EngineeringObjectDisposedException`. Re-fetch the object (e.g. via `ObjectIdentifierProvider`, see [`performance-and-caching`](../performance-and-caching/SKILL.md)) instead of reusing the old reference.
- **Missing Products/Packages:** Opening a project that requires TIA Portal packages which are not installed throws `MissingProductsException` with a clear message identifying the missing product(s). When *attaching* to an already-open, unsupported project instead of opening it, there is no exception — the project's and session's compositions are simply empty; check for this case explicitly.
- **Licensing and Firewall:** A missing product/option license throws `LicenseNotFoundException`; a firewall denial throws `EngineeringSecurityException`. See [`licensing-and-firewall`](../licensing-and-firewall/SKILL.md) for the full access-control model.
- **Make It Robust:** Always wrap engineering work in `using`/`try-finally` so `ExclusiveAccess` and transactions are released even on failure. Prefer retrying or re-attaching on transient states over crashing.
