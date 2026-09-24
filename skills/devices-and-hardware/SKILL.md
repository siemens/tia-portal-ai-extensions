---
name: devices-and-hardware
description: Devices and hardware configuration in TIA Portal Openness. Use when creating devices, finding CPUs, configuring PROFINET subnets, I/O systems, and network interfaces.
metadata:
  siemens-depends-on: "openness-base"
---

# Devices and Hardware

## Overview

Devices represent the hardware components of a TIA Portal project, including PLCs, ET 200 stations, HMIs, and drives. Devices are created using order numbers (`CreateWithItem`), contain `DeviceItem` hierarchies, and expose hardware services such as `NetworkInterface`. PROFINET communication is configured through subnets, I/O systems, and transfer areas. Device items can be queried by classification (e.g., CPU) or by attribute info.

## 🛑 MANDATORY CHECK BEFORE CODING: TypeIdentifier Requirement

**BEFORE you write ANY code that creates devices, you MUST ask the user for the `TypeIdentifier` of every device they want to create.**

This is a **blocking requirement** — do NOT proceed to generate code without confirmed TypeIdentifiers.

### How to Ask

Use the `ask_user` tool with a clear message. Example:

```
I need the TypeIdentifier for the device you want to create.

To find the TypeIdentifier in TIA Portal:
1. Go to Options → Settings → Hardware Configuration
2. Enable "Display of the Type Identifier"
3. Browse to the device in the hardware catalog
4. Copy the TypeIdentifier (e.g., OrderNumber:6ES7 515-2UM01-0AB0/V2.9)

What TypeIdentifier should I use for [the device]?
```

### What You Must NOT Do

- ❌ Do NOT assume or guess TypeIdentifiers
- ❌ Do NOT use example TypeIdentifiers from this documentation in production code
- ❌ Do NOT skip asking just because the user mentioned a device name (e.g., "S7-1500") — the exact TypeIdentifier includes version info that is required
- ❌ Do NOT start generating code before you have all TypeIdentifiers

## Required Namespaces

```csharp
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`

**NOTE:** All device, hardware, and network types are defined in `Siemens.Engineering.Base.dll`, but **not** all in the root `Siemens.Engineering` namespace — the assembly is correct, the namespace differs per type. Confirmed mapping:
- `Siemens.Engineering` — `TiaPortal`, `Project`
- `Siemens.Engineering.HW` — `Device`, `DeviceComposition`, `DeviceItem`, `DeviceItemClassifications`, `Node`, `Subnet`, `IoSystem`, `IoController`, `IoConnector`, `NetType`
- `Siemens.Engineering.HW.Features` — `NetworkInterface`, `NetworkPort`

The DLL `Siemens.Engineering.HW.dll` does NOT exist as a separate file — `HW` and `HW.Features` are namespaces inside `Siemens.Engineering.Base.dll`. See [`openness-base`](../openness-base/SKILL.md) for the full verified namespace map and how to probe an unlisted type yourself.

## Common Patterns

### Create Device with Order Number (CreateWithItem)

**Description:** Add a device to the project using its Siemens order number and version. Devices can be created under `Project.Devices` or `Project.UngroupedDevicesGroup` for decentralized stations.

**Example:**

```csharp
var plc = project.Devices.CreateWithItem("OrderNumber:6ES7 515-2UM01-0AB0/V2.9", "", "");
var et200 = project.UngroupedDevicesGroup.Devices.CreateWithItem("OrderNumber:6ES7 155-6AU00-0CN0/V3.0", "", "");
```

**Key Types and Methods:**
- `DeviceGroup.CreateWithItem(string orderNumber, string name, string comment)` — creates a device from its order number
- `UngroupedDevicesGroup` — container for devices not nested inside another device

🛑 **Device naming — do not invent or hardcode a name when the user hasn't provided one.** The `name` parameter of `CreateWithItem` accepts an empty string `""`, and TIA Portal will then auto-generate the default station name (e.g. `"S7-1500/ET200MP station_1"`, incrementing to `_2`, `_3`, ... as needed to stay unique). If your code instead hardcodes a literal like `"PLC_1"` and that name already exists in the target project (very likely on a real/shared project, or on repeat test runs against the same project), `CreateWithItem` throws `EngineeringTargetInvocationException` with a message like `Invalid 'Name' parameter with "PLC_1" value`.

**Rule of thumb:**
- If the user explicitly specifies a device name, use it as given.
- If the user does NOT specify a name, pass `""` and let TIA Portal auto-name the device — do NOT default to a hardcoded literal such as `"PLC_1"` or `"Drive_1"`.
- Only rename after creation (e.g. via the `Name` attribute) if the user asks for a specific final name and you've confirmed uniqueness is not already handled by auto-naming.

```csharp
// User gave no name -> let TIA Portal auto-name; safe to repeat against the same project
var plc = project.Devices.CreateWithItem(plcTypeIdentifier, "", "");

// User explicitly asked for "PLC_Main" -> use it, but be aware it can still collide
var plc = project.Devices.CreateWithItem(plcTypeIdentifier, "PLC_Main", "");
```

**Note:** For a CPU like an S7-1500, `CreateWithItem` produces a full **station** device, e.g. named `"S7-1500/ET200MP station_1"` — the returned `Device` is the station, **not** the CPU. The CPU itself is a child `DeviceItem` of that station (find it via `DeviceItemClassifications.CPU`, see below). Callers that assume the returned `Device.Name` is the CPU name will look in the wrong place.

### Find CPU DeviceItem by Classification

**Description:** Locate the CPU device item within a device by filtering on its `Classification` property. Use `DeviceItemClassifications.CPU` to find processor modules.

**Example:**

```csharp
var device = Project.Devices.First(x => x.Name == "PLC_S120Democase");
var cpu = device.DeviceItems.Single(x => x.Classification == DeviceItemClassifications.CPU);
```

**Key Types and Methods:**
- `DeviceItem.Classification` — categorizes the device item type
- `DeviceItemClassifications.CPU` — constant for CPU classification

### Get NetworkInterface Service

**Description:** Obtain the `NetworkInterface` service from a device item (e.g., PROFINET interface module) to configure network settings. Check `InterfaceType` to verify the interface is Ethernet-capable.

**Example:**

```csharp
var networkInterfacePlc = cpu.DeviceItems
    .First(x => x.Name.Contains("PROFINET")).GetService<NetworkInterface>();
var nwItf = deviceItem.GetService<NetworkInterface>() is NetworkInterface nw && nw.InterfaceType == NetType.Ethernet;
```

**Key Types and Methods:**
- `NetworkInterface` — service for network interface configuration
- `NetworkInterface.InterfaceType` — type of network interface
- `NetType.Ethernet` — constant for Ethernet interfaces

### Supplementary DeviceItems Are Auto-Created by TIA Portal

**Description:** When you place the main component of a device — such as a PLC CPU, a drive Control Unit, or a distributed-I/O head module — TIA Portal automatically creates the supporting `DeviceItem`s for that component (for example network interfaces, port items, and rack items).

**Key points:**
- Do **not** try to create PROFINET interface or port `DeviceItem`s explicitly; they already exist immediately after `CreateWithItem`.
- Recurse through `device.DeviceItems` after placement to find the auto-created items you want to configure via `GetService<NetworkInterface>()`, `GetService<NetworkPort>()`, or other services.
- Only user-added extensions beyond the base unit (additional modules, optional boards, rack-inserted hardware) need explicit placement calls.

### Create and Connect to Subnet

**Description:** Create a PROFINET subnet and connect multiple device nodes to it. A node can create and auto-connect to a subnet, then other nodes can connect to the same subnet.

**Example:**

```csharp
var plcSubnet = plcNode.ConnectedSubnet;
plcSubnet ??= plcNode.CreateAndConnectToSubnet("TestSubnet");
if (et200Node.ConnectedSubnet == null)
    et200Node.ConnectToSubnet(plcSubnet);
```

**Key Types and Methods:**
- `Node.ConnectedSubnet` — the subnet this node is already connected to (nullable)
- `Node.CreateAndConnectToSubnet(string)` — creates a subnet and connects the node
- `Node.ConnectToSubnet(Subnet)` — connects a node to an existing subnet

🛑 **`ConnectToSubnet()` throws if the node is already connected** — always guard with `Node.ConnectedSubnet == null` first, exactly like `ConnectToPort` below.

🛑 **Name collisions are silent, not exceptions:** `CreateAndConnectToSubnet(name)` does **not** throw if a subnet with that name already exists elsewhere in the project — it silently returns/joins the existing one. Reusing a literal name (e.g. `"TestSubnet"`) across multiple PLC/device pairs wires new devices onto an unrelated, pre-existing subnet instead of creating a dedicated one. Derive the name from the device identity instead: `$"PROFINET_{plc.Name}"`. See [`networks-and-drivecliq`](../networks-and-drivecliq/SKILL.md) for the full write-up of this failure mode and its downstream symptoms.

### Create and Connect IoSystem

**Description:** Establish I/O control between a controller (e.g., PLC) and an I/O device (e.g., ET 200). Create an `IoSystem` on the controller side and connect the I/O device's `IoConnector`.

**Example:**

```csharp
var ioConnector = networkInterfaceEt200.IoConnectors.First();
var plcIoSystem = networkInterfacePlc.IoControllers.First().IoSystem ??
                  networkInterfacePlc.IoControllers.First().CreateIoSystem("TestIOSystem");
try
{
    ioConnector.ConnectToIoSystem(plcIoSystem);
}
catch (Exception)
{
    // ConnectToIoSystem throws if the device is already assigned to an IO system — safe to ignore
}
```

**Key Types and Methods:**
- `IoConnector` — I/O connection point on a device
- `IoController` — I/O control point on a controller
- `IoController.CreateIoSystem(string)` — creates a new I/O system
- `IoConnector.ConnectToIoSystem(IoSystem)` — connects to an existing I/O system; **throws if already connected/assigned** — wrap in try/catch or check first
- Same name-collision caveat as subnets applies to `CreateIoSystem(name)` — scope the name per PLC (e.g. `$"IO_System_{plc.Name}"`)

**Wiring order:** create the `Subnet` first, connect the controller `Node`, create the `IoSystem` on the controller side, then connect each device `IoConnector`.

### Create Multicast Transfer Area

**Description:** Create multicast-capable transfer areas between network interfaces for data exchange (e.g., DDX — Direct Data Exchange). Can be created from an existing transfer area template or explicitly configured.

**Example:**

```csharp
var newTransferArea = nwItf.MulticastableTransferAreas.Create(existingTransferArea, existingTransferArea.Type);
var newTa = nwItf.MulticastableTransferAreas.Create(partnerNwItf, TransferAreaType.DDX, "Plc2ToLead", 1);
```

**Key Types and Methods:**
- `NetworkInterface.MulticastableTransferAreas` — collection for multicast transfer areas
- `TransferAreaType.DDX` — direct data exchange transfer area type

### Port-to-Port Topology Connections

**Description:** `NetworkPort` is the physical-port service used for topology (cabling) connections. Always guard `ConnectToPort` with a `ConnectedPorts.Contains` check — the API throws if the link already exists.

**Example:**

```csharp
var port1 = deviceItem1.GetService<NetworkPort>();
var port2 = deviceItem2.GetService<NetworkPort>();

if (port1 != null && port2 != null && !port1.ConnectedPorts.Contains(port2))
    port1.ConnectToPort(port2);

// Remove an existing connection
if (port1.ConnectedPorts.Contains(port2))
    port1.DisconnectFromPort(port2);
```

**Key Types and Methods:**
- `NetworkPort` — service (`Siemens.Engineering.HW.Features`) on a port `DeviceItem`
- `NetworkPort.ConnectedPorts` — currently connected port objects
- `NetworkPort.ConnectToPort(NetworkPort)` — establishes a topology link
- `NetworkPort.DisconnectFromPort(NetworkPort)` — removes a topology link

### Find DeviceItems by Attribute Info

**Description:** Query device items by the attributes they expose. Use `GetAttributeInfos()` to inspect available attribute names and filter device items accordingly.

**Example:**

```csharp
var profinetInterfaces = cpu.DeviceItems
    .Where(d => d.GetAttributeInfos().Select(x => x.Name).Contains("PnSendClock")).ToList();
```

**Key Types and Methods:**
- `DeviceItem.GetAttributeInfos()` — returns metadata about available attributes on the device item

### Recursing Through Nested Device Groups (`DeviceUserGroup.Groups`)

**Description:** `Project.DeviceGroups` returns a collection of `DeviceUserGroup` objects. Each `DeviceUserGroup` exposes **both** a `.Devices` collection (devices directly in that group) **and** a `.Groups` collection of nested subgroups. Iterating only `.Devices` at the top level silently skips every device that sits inside a subgroup — device groups in real projects are commonly nested multiple levels deep (e.g. a project → station group → line group → individual device group), so recursion into `.Groups` is required to reach every device.

**Example:**

```csharp
static void ProcessGroup(DeviceUserGroup group, string path)
{
    foreach (Device device in group.Devices)
        ProcessDevice(device, $"{path}/{device.Name}");

    // Recurse into nested subgroups — without this, devices in subgroups are missed
    foreach (DeviceUserGroup subGroup in group.Groups)
        ProcessGroup(subGroup, $"{path}/{subGroup.Name}");
}

// Entry point: cover all three device locations in a project
foreach (Device device in project.Devices)
    ProcessDevice(device, device.Name);

foreach (DeviceUserGroup group in project.DeviceGroups)
    ProcessGroup(group, group.Name);

foreach (Device device in project.UngroupedDevicesGroup.Devices)
    ProcessDevice(device, device.Name);
```

**Key Types and Methods:**
- `Project.DeviceGroups` — top-level `DeviceUserGroup` collection
- `DeviceUserGroup.Devices` — devices directly inside this group (not recursive)
- `DeviceUserGroup.Groups` — nested subgroups; must be walked recursively to reach all devices
- To visit every device in a project, combine `project.Devices`, recursive `project.DeviceGroups`, and `project.UngroupedDevicesGroup.Devices` — devices can legitimately sit in any of the three.

### `OptionalIoDevice` Attribute on the PROFINET Interface DeviceItem

**Description:** The "optional IO device" flag seen in the TIA Portal UI (under the PROFINET interface properties of a PLC's CPU DeviceItem, or the corresponding HM/drive interface of a Startdrive device) is exposed via Openness as a plain boolean attribute named `OptionalIoDevice`. It lives on the PROFINET **interface** `DeviceItem` itself (the item representing the `X1`/`PN` port, not the parent `Device`, not the CPU/HM `DeviceItem` that owns it, and not a dedicated service). It behaves like any other read/write attribute — discoverable via `GetAttributeInfos()` and readable/writable via `GetAttribute`/`SetAttribute`, no special service (`NetworkInterface`, etc.) is required to access it.

**Example:**

```csharp
// Discover the attribute by name on a PROFINET interface DeviceItem (defensive — avoids
// hardcoding exact casing/locale differences across TIA Portal versions)
var attrInfo = interfaceItem.GetAttributeInfos()
    .FirstOrDefault(a => a.Name.IndexOf("OptionalIoDevice", StringComparison.OrdinalIgnoreCase) >= 0);

if (attrInfo != null && interfaceItem.GetAttribute(attrInfo.Name) is bool isOptional)
{
    // Read
    Console.WriteLine($"{interfaceItem.Name}: OptionalIoDevice = {isOptional}");

    // Write — e.g. clear the flag so the device becomes mandatory again
    interfaceItem.SetAttribute(attrInfo.Name, false);
}
```

**Key Types and Methods:**
- `DeviceItem.GetAttributeInfos()` / `GetAttribute(name)` / `SetAttribute(name, value)` — standard attribute access, no special service needed
- Attribute lives on the PROFINET **interface** `DeviceItem` (e.g. named `PN`, `X1`, or similar depending on device family), reached by recursing into `DeviceItems` from the CPU/HM `DeviceItem`
- As with any attribute write via Openness, the change is in-memory only until `Project.Save()` is called (or the user saves in the UI)

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `Devices.CreateWithItem(orderNumber, name, comment)` | Create a device from order number — pass `name: ""` when the user gave no explicit name, so TIA Portal auto-generates a unique name instead of throwing on a collision |
| `DeviceItem.Classification == CPU` | Find CPU device items |
| `deviceItem.GetService<NetworkInterface>()` | Get network interface configuration |
| `Node.CreateAndConnectToSubnet(name)` | Create and join a PROFINET subnet |
| `IoController.CreateIoSystem(name)` | Create an I/O system on a controller |
| `MulticastableTransferAreas.Create()` | Create DDX transfer areas |
| `deviceItem.GetService<NetworkPort>()` | Get physical port for topology wiring |
| `port.ConnectToPort(otherPort)` | Establish port-to-port topology link (guard with `Contains` check first) |
| `DeviceItem.GetAttributeInfos()` | Inspect device item attributes |
| `DeviceUserGroup.Groups` (recursive) | Reach devices nested in subgroups — `.Devices` alone only covers the current group level |
| `interfaceItem.GetAttribute("OptionalIoDevice")` / `SetAttribute(...)` | Read/write the optional-IO-device flag on the PROFINET interface `DeviceItem` |

## Related Files

- [`online-and-download`](../online-and-download/SKILL.md) — devices are the targets for online operations and downloads
- [`security`](../security/SKILL.md) — UMAC security is configured per-device

## Exception Handling

- `EngineeringTargetInvocationException` with message like `Invalid 'Name' parameter with "PLC_1" value` is thrown when `CreateWithItem` is given a hardcoded literal name that already exists in the project. Avoid this entirely by passing `""` when the user has not specified a name (see naming rule above), instead of catching/retrying after the fact.
- `EngineeringException` is thrown if the order number is invalid or the device definition is not installed
- `InvalidOperationException` may occur when connecting nodes to incompatible subnets or I/O systems
- Null checks are required for `Node.ConnectedSubnet` and `IoController.IoSystem` as they may not exist yet
- `ConnectToPort` throws if the port link already exists — always guard with `ConnectedPorts.Contains(...)` before calling
- `ConnectToSubnet` / `ConnectToIoSystem` likewise throw if the link already exists — guard with `ConnectedSubnet == null` or wrap in try/catch
- `CreateAndConnectToSubnet(name)` / `CreateIoSystem(name)` do **not** throw on a name collision with an existing subnet/IO-system elsewhere in the project — they silently attach to it. Scope names to the device identity to avoid silently misrouting devices (see [`networks-and-drivecliq`](../networks-and-drivecliq/SKILL.md))
