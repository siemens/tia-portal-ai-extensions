---
name: online-and-download
description: Online connection and download operations for TIA Portal. Use when connecting to CPU devices via OnlineProvider, downloading PLC software, configuring connection modes, and handling passwords.
metadata:
  siemens-depends-on: "openness-base, devices-and-hardware"
---

# Online and Download

## Overview

Online and download operations enable communication between the engineering station and the target device. The location of `OnlineProvider` and `DownloadProvider` depends on the device type:

| Device Type | Provider Location |
|---|---|
| **Step 7 PLC** | `OnlineProvider` and `DownloadProvider` are services on the **CPU** (`DeviceItemClassifications.CPU`) |
| **StartDrive** | `OnlineProvider` and `DownloadProvider` are services on the **headmodule** of the Device (`DeviceItemClassifications.HM`) |

When the device type is not known in advance, auto-detect by first checking for a headmodule (`HM`), then falling back to a CPU (`CPU`).

Both providers share a common target configuration type — `ConfigurationTargetInterface` from `Siemens.Engineering.Connection` — which is obtained by navigating: mode → PC interface → target interface. Password callbacks are supported for protected downloads.

## Required Namespaces

```csharp
using Siemens.Engineering.Connection;
using Siemens.Engineering.Download;
using Siemens.Engineering.Download.Configurations;
using Siemens.Engineering.HW;
using Siemens.Engineering.Online;
using Siemens.Engineering.Upload;
using System.Security;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`

## Common Patterns

### Get Provider with Auto-Detection

**Description:** When the device type is not known in advance, auto-detect the provider object by checking for a headmodule (`HM`, StartDrive) first, then falling back to a CPU (`CPU`, Step 7 PLC).

**Example (auto-detect):**

```csharp
DeviceItem GetProviderObject(DeviceItem device)
{
    var headmodule = device.Items.FirstOrDefault(x => x.Classification == DeviceItemClassifications.HM);
    if (headmodule is not null) return headmodule;

    var cpu = device.Items.FirstOrDefault(x => x.Classification == DeviceItemClassifications.CPU);
    return cpu;
}

var providerObject = GetProviderObject(device);
var onlineProvider = providerObject.GetService<OnlineProvider>();
var downloadProvider = providerObject.GetService<DownloadProvider>();
```

**Example (explicit, Step 7 PLC):**

```csharp
var onlineProvider = cpu.GetService<OnlineProvider>();
var downloadProvider = cpu.GetService<DownloadProvider>();
```

**Example (explicit, StartDrive):**

```csharp
var headmodule = device.Items.First(x => x.Classification == DeviceItemClassifications.HM);
var onlineProvider = headmodule.GetService<OnlineProvider>();
var downloadProvider = headmodule.GetService<DownloadProvider>();
```

**Key Types and Methods:**
- `DeviceItemClassifications.HM` — classification for headmodule (StartDrive)
- `DeviceItemClassifications.CPU` — classification for CPU (Step 7 PLC)
- `device.Items` — collection of all items in the device

### Common Target Configuration

**Description:** Both `OnlineProvider` and `DownloadProvider` use the same `ConfigurationTargetInterface` type (from `Siemens.Engineering.Connection`) as their target configuration. This is a unified type that works for both online connections and downloads. Obtain it by navigating: mode → PC interface → target interface.

**Example:**

```csharp
using Siemens.Engineering.Connection;

// For OnlineProvider
var configuration = onlineProvider.Configuration;
var configurationMode = configuration.Modes.Find("PN/IE");
var pcInterface = configurationMode.PcInterfaces.Find(interfaceName, 1);
ConfigurationTargetInterface targetConfiguration = pcInterface.TargetInterfaces[0];

// For DownloadProvider
var downloadConfiguration = downloadProvider.Configuration;
var downloadMode = downloadConfiguration.Modes.Find("PN/IE");
var downloadPcInterface = downloadMode.PcInterfaces.Find(interfaceName, 1);
ConfigurationTargetInterface downloadTargetConfiguration = downloadPcInterface.TargetInterfaces[0];
```

**Key Types:**
- `ConfigurationTargetInterface` — common target configuration type for both online and download operations (namespace: `Siemens.Engineering.Connection`)

### GoOnline via OnlineProvider

**Description:** Establish an online connection to the device. Get the `OnlineProvider` by auto-detecting (HM or CPU), apply the `ConfigurationTargetInterface` and call `GoOnline()`. After calling `GoOnline()`, **poll `OnlineProvider.State` until it reaches `OnlineState.Online`** — the method returns before the connection is fully established.

**Example:**

```csharp
var providerObject = GetProviderObject(device);
var onlineProvider = providerObject.GetService<OnlineProvider>();
onlineProvider.Configuration.ApplyConfiguration(targetConfiguration);
onlineProvider.GoOnline();

// Poll until fully online — GoOnline() returns before connection is established
while (onlineProvider.State != OnlineState.Online)
    Thread.Sleep(200);
```

**Key Types and Methods:**
- `OnlineProvider` — service for online connection operations (HM on StartDrive, CPU on Step 7)
- `OnlineConfiguration.ApplyConfiguration(ConfigurationTargetInterface)` — applies the selected configuration
- `OnlineProvider.GoOnline()` — initiates the online connection (returns immediately, not when complete)
- `OnlineProvider.GoOffline()` — disconnects from the device
- `OnlineProvider.State` — current connection state; poll against `OnlineState.Online`
- `OnlineState.Online` — enum value indicating the device is fully connected

### Download via DownloadProvider with Password

**Description:** Download the PLC software to the device. Get the `DownloadProvider` by auto-detecting (HM or CPU), then execute `Download()` with a `ConfigurationTargetInterface`, password callback, progress callback, and download options. Use `DownloadOptions.SoftwareOnlyChanges` for software-only downloads.

**⚠️ V21 IMPORTANT — Download is fire-and-forget:** In TIA Portal V21, `Download()` returns immediately — the device has **not** finished processing the download when the call returns. For StartDrive devices, you must go online afterwards and poll `OnlineDriveObject.Parameters` to confirm completion (see "Wait for StartDrive Download Completion" below).

**⚠️ IMPORTANT — Cache the `DownloadProvider` instance:** `ConfigurationTargetInterface` objects are bound to the `DownloadProvider` instance they were enumerated from. If you call `GetService<DownloadProvider>()` again later (creating a new instance), those target objects are silently invalid — the download will use the device default interface instead of the one the user selected. **Cache the provider** at enumeration time and reuse it for the actual download call.

**Example:**

```csharp
// CORRECT: cache at enumeration time, reuse for download
private DownloadProvider _downloadProvider;

// During network settings setup:
_downloadProvider = providerObject.GetService<DownloadProvider>();
var modes = _downloadProvider.Configuration.Modes; // enumerate ConfigurationTargetInterface here

// During actual download — reuse the SAME instance:
_downloadProvider.Download(targetConfiguration, preDownload =>
{
    if (preDownload is DownloadPasswordConfiguration dpc)
        dpc.SetPassword(password);
}, _ => { }, DownloadOptions.SoftwareOnlyChanges);

// WRONG: creating a new instance loses the ConfigurationTargetInterface binding
var freshProvider = providerObject.GetService<DownloadProvider>(); // new instance!
freshProvider.Download(targetConfiguration, ...); // silently uses default interface
```

**Key Types and Methods:**
- `DownloadProvider` — service for download operations (HM on StartDrive, CPU on Step 7)
- `DownloadProvider.Download(ConfigurationTargetInterface, ..., DownloadOptions)` — executes the download
- `DownloadPasswordConfiguration.SetPassword(SecureString)` — sets the download password
- `DownloadOptions.SoftwareOnlyChanges` — flag to download only software changes
- `DownloadResult` — result of the download operation

---

### Wait for StartDrive Download Completion (V21)

**Description:** In TIA Portal V21, `DownloadProvider.Download()` is fire-and-forget — it returns before the drive has processed the download. After calling `GoOnline()` and polling for `OnlineState.Online`, poll the first readable parameter (`r`-prefix) on the `OnlineDriveObject` until its value is non-null. This confirms the drive has fully applied the downloaded configuration.

**Example:**

```csharp
// After Download() and GoOnline() + polling for OnlineState.Online:
DeviceItem deviceItem = driveObject.Parent<DeviceItem>();
var onlineContainer = deviceItem?.GetService<OnlineDriveObjectContainer>();
var onlineAxis = onlineContainer?.OnlineDriveObjects
    .FirstOrDefault(o => o.DriveObjectNumber == driveObject.DriveObjectNumber);

if (onlineAxis != null)
{
    int attempts = 0;
    while (onlineAxis.Parameters.FirstOrDefault(x => x.Name.StartsWith("r"))?.Value == null
           && attempts++ < 150) // max ~15 seconds
        Thread.Sleep(100);
}
```

**Key Types and Methods:**
- `OnlineDriveObject.Parameters` — live parameter collection; values are `null` until drive is ready
- `DriveObject.Parent<DeviceItem>()` — navigate up to the containing `DeviceItem`
- `OnlineDriveObjectContainer` — see [`drive-objects`](../drive-objects/SKILL.md) Rule 15

**Note:** This pattern only applies to **StartDrive (SINAMICS) devices**. PLC and HMI downloads do not require this check.

---

### Upload Parameters from StartDrive Device

**Description:** For **StartDrive (SINAMICS) devices only** — upload the current parameter values from the device into the TIA Portal project. Uses `ParameterUploadProvider`, which is available exclusively on drive headmodules. This is not supported for PLCs, HMIs, or other device types.

**Example:**

```csharp
using Siemens.Engineering.Upload;

var headmodule = device.DeviceItems.First(x => x.Classification == DeviceItemClassifications.HM);
var uploadProvider = headmodule.GetService<ParameterUploadProvider>();
if (uploadProvider == null)
    throw new InvalidOperationException("ParameterUploadProvider not available — device may not be a StartDrive device.");

uploadProvider.ParameterUpload(targetConfiguration, null, _ => { });
```

**Key Types and Methods:**
- `ParameterUploadProvider` — upload service; only available on StartDrive headmodules (`DeviceItemClassifications.HM`)
- `ParameterUploadProvider.ParameterUpload(ConfigurationTargetInterface, ...)` — uploads parameters from device to project
- Namespace: `Siemens.Engineering.Upload`

**Note:** `ParameterUploadProvider` returns `null` on CPU (Step 7 PLC) device items. Always null-check before use.

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `device.Items.FirstOrDefault(x => x.Classification == DeviceItemClassifications.HM)` | Find headmodule (StartDrive) |
| `device.Items.FirstOrDefault(x => x.Classification == DeviceItemClassifications.CPU)` | Find CPU (Step 7 PLC) |
| `providerObject.GetService<OnlineProvider>()` | Get online provider from HM or CPU |
| `providerObject.GetService<DownloadProvider>()` | Get download provider from HM or CPU (cache instance!) |
| `headmodule.GetService<ParameterUploadProvider>()` | Get upload provider (StartDrive HM only) |
| `OnlineProvider.GoOnline()` | Initiate online connection (poll `State` for completion) |
| `OnlineProvider.GoOffline()` | Disconnect from device |
| `OnlineProvider.State` | Current connection state; compare to `OnlineState.Online` |
| `while (provider.State != OnlineState.Online) Thread.Sleep(200)` | Wait for connection to be fully established |
| `OnlineProvider.Configuration.ApplyConfiguration(targetConfig)` | Apply selected connection settings |
| `DownloadProvider.Download(targetConfig, ..., DownloadOptions)` | Download software to the device (fire-and-forget in V21!) |
| `DownloadPasswordConfiguration.SetPassword(SecureString)` | Provide password for protected downloads |
| `ConfigurationTargetInterface` | Common target config type for both online and download |
| `DownloadOptions.SoftwareOnlyChanges` | Download only software modifications |
| `ParameterUploadProvider.ParameterUpload(targetConfig, null, _ => {})` | Upload parameters from StartDrive device to project |

## Related Files

- [`devices-and-hardware`](../devices-and-hardware/SKILL.md) — device and CPU hardware configuration
- [`blocks`](../blocks/SKILL.md) — blocks are the software artifacts being downloaded
- [`security`](../security/SKILL.md) — master passwords may be required for download
- [`drive-objects`](../drive-objects/SKILL.md) — `OnlineDriveObject` access for download completion polling (Rules 14–16)

## Exception Handling

- `EngineeringException` is thrown if the device is unreachable, the connection fails, or the download is rejected
- `OnlineProvider.GoOffline()` is a native API method that does **not** require applying a configuration — simply call it directly
- `GoOnline()` returns immediately — always poll `OnlineProvider.State != OnlineState.Online` before proceeding
- In TIA Portal V21, `Download()` is fire-and-forget — poll `OnlineDriveObject.Parameters` for completion on StartDrive devices
- `ConfigurationTargetInterface` objects are tied to the `DownloadProvider` instance that enumerated them — cache the provider, never create a fresh instance for the download call
- `ParameterUploadProvider` is `null` on non-StartDrive device items — always null-check before use
- `DownloadResult` should be inspected after download to verify success; failures may indicate version conflicts, missing licenses, or hardware incompatibilities
- Password callbacks must handle `DownloadPasswordConfiguration` correctly — failing to provide a valid password for a protected project will cause the download to fail
