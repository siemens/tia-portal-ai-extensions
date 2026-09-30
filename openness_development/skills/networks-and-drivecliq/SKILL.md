---
name: networks-and-drivecliq
description: Network and DriveCliq configuration for SINAMICS drives. Use when connecting/disconnecting DriveCliq ports, configuring PROFINET interfaces, and discovering IO system topology.
metadata:
  siemens-depends-on: "openness-base, devices-and-hardware, hardware-and-modules"
---

# Networks and DriveCliq

## Overview

Network configuration in TIA Portal Openness covers DriveCliq topology wiring, PROFINET interface configuration, and IO system traversal. Use `NetworkPort` services to connect and disconnect DriveCliq links between devices. Access `NetworkInterface` for PROFINET node configuration (IP address, subnet mask, device name). Walk from a CPU through its network interfaces to discover connected IO systems and SINAMICS devices.

## Required Namespaces

```csharp
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`
- `Siemens.Engineering.Startdrive.dll`

## Common Patterns

### Get NetworkPorts from DriveCliq Interface

**Description:** Extract all network ports from a DriveCliq interface device item. Navigate the device item hierarchy to locate the DriveCliq interface, then retrieve `NetworkPort` services.

**Example:**

```csharp
var driveCliqInterface = driveAxis.DeviceItems.First().DeviceItems.First();
var axisPorts = driveCliqInterface.DeviceItems
    .Select(x => x.GetService<NetworkPort>())
    .ToList();
```

**Key Types and Methods:**
- `NetworkPort` — service representing a physical or logical network port
- `DeviceItem.DeviceItems` — hierarchical child items of a device
- `GetService<NetworkPort>()` — retrieves the port service from a device item

### DisconnectFromPort

**Description:** Disconnect a network port from its connected counterpart. Iterate through `ConnectedPorts` and call `DisconnectFromPort()` for each connection.

**Example:**

```csharp
foreach (var port in axisPorts)
{
    var connectedPort = port.ConnectedPorts.FirstOrDefault();
    if (connectedPort != null)
    {
        port.DisconnectFromPort(connectedPort);
    }
}
```

**Key Types and Methods:**
- `NetworkPort.ConnectedPorts` — collection of ports currently connected to this port
- `NetworkPort.DisconnectFromPort(targetPort)` — removes the connection

### ConnectToPort

**Description:** Connect two network ports together to establish a DriveCliq link.

**Example:**

```csharp
var firstCuNetworkPort = firstCuPort.GetService<NetworkPort>();
firstAxisPort.ConnectToPort(firstCuNetworkPort);
```

**Key Types and Methods:**
- `NetworkPort.ConnectToPort(targetPort)` — creates a connection between two ports
- Ports must be compatible (e.g., DriveCliq-to-DriveCliq or PROFINET-to-PROFINET)

### NetworkInterface — Get Nodes and Set Attributes

**Description:** Access PROFINET interface nodes and configure IP address, subnet mask, and device name via `SetAttribute()`.

**Example:**

```csharp
var networkInterface = profinetInterface.GetService<NetworkInterface>();
var node = networkInterface.Nodes.First();
node.SetAttribute("Address", "192.168.0.2");
node.SetAttribute("SubnetMask", "255.255.0.0");
node.SetAttribute("PnDeviceNameAutoGeneration", false);
node.SetAttribute("PnDeviceName", "name");
```

**Key Types and Methods:**
- `NetworkInterface` — service for PROFINET network configuration
- `NetworkInterface.Nodes` — collection of network nodes (IP configurations)
- `Node.SetAttribute("Address", ip)` — sets the IP address
- `Node.SetAttribute("PnDeviceName", name)` — sets the PROFINET device name

### 🛑 Subnet / IO-system names must be unique per PLC-drive pair — never hardcode a literal name

**Description:** `CreateAndConnectToSubnet(name)`/`CreateIoSystem(name)` silently succeed if a subnet/IO-system with that name **already exists elsewhere in the project** — the call does not throw, and the returned `Subnet`/`IoSystem` looks valid. But reusing a fixed literal name (e.g. `"PROFINET_1"`) across multiple PLC/drive pairs wires the new devices onto an **existing, unrelated** PLC's subnet/IO system instead of creating a dedicated one. This produces no exception at connect time — it silently misroutes devices, and the failure only surfaces much later (e.g. a drive hardware-connection call fails with an opaque "Target not available" because the querying PLC was never actually the IO controller for that shared, reused IO system). This is one of the most expensive-to-diagnose classes of bug encountered with this API.

**Rule:** derive subnet/IO-system names from the PLC/device identity, never from a literal constant, whenever a tool may run more than once or handle more than one PLC/drive pair:

```csharp
// WRONG — fine for a single-run demo, a latent bug generator for anything else
var subnet = plcNode.CreateAndConnectToSubnet("PROFINET_1");
var ioSystem = plcInterface.IoControllers.First().CreateIoSystem("IO_System_1");

// CORRECT — scope the name to the specific PLC/device identity
var subnet = plcNode.CreateAndConnectToSubnet($"PROFINET_{plc.Name}");
var ioSystem = plcInterface.IoControllers.First().CreateIoSystem($"IO_System_{plc.Name}");
```

**Sanity check before proceeding:** obtaining an `IoSystem` (e.g. via `IoConnector.ConnectToIoSystem`) does **not** guarantee the PLC you intended is the actual IO controller of that system — especially if the name was reused. Verify identity before relying on it:

```csharp
IoController controller = networkInterfacePlc.IoControllers.First();
IoSystem ioSystem = controller.IoSystem;
if (ioSystem == null || ioSystem != expectedIoSystem)
    throw new InvalidOperationException(
        $"PLC '{plc.Name}' is not the IO controller of the expected IO system — likely a reused subnet/IO-system name collision.");
```

### 🛑 Connect calls throw if the link already exists — always guard

**Description:** `ConnectToIoSystem`, `ConnectToSubnet`, and `ConnectToPort` all throw if the target is already connected. Guard every one of them, mirroring the `ConnectedPorts.Contains(...)` pattern used for `ConnectToPort` in [`devices-and-hardware`](../devices-and-hardware/SKILL.md).

```csharp
if (plcNode.ConnectedSubnet == null)
    plcNode.ConnectToSubnet(subnet);

try
{
    ioConnector.ConnectToIoSystem(plcIoSystem);
}
catch (Exception)
{
    // ConnectToIoSystem throws if the device is already assigned to an IO system — safe to ignore
    // (no confirmed pre-check property exists; guard with try/catch, same as devices-and-hardware.md)
}
```

### GetAllConnectedIoSystems from CPU

**Description:** Walk from a CPU device item through its network interfaces to find all connected IO systems. Useful for discovering the full IO topology.

**Example:**

```csharp
var allNetworkInterfaces = deviceItem.DeviceItems
    .Select(x => x.GetService<NetworkInterface>())
    .Where(x => x != null);

var ioSystems = allNetworkInterfaces
    .SelectMany(x => x.IoControllers)
    .Select(x => x.IoSystem)
    .Where(x => x != null);
```

**Key Types and Methods:**
- `NetworkInterface.IoControllers` — collection of IO controllers on this interface
- `IoController.IoSystem` — reference to the IO system

### Get Connected IO Devices from IoSystem

**Description:** Access `ConnectedIoDevices` on an IO system to find connected SINAMICS devices.

**Example:**

```csharp
var connectedIoDevices = connectedIoSystems
    .SelectMany(ioSystem => ioSystem.ConnectedIoDevices);
```

**Key Types and Methods:**
- `IoSystem.ConnectedIoDevices` — collection of devices connected to this IO system
- Combine with `GetService<DriveObjectContainer>() != null` to filter for SINAMICS devices

### Physical port topology vs. logical subnet / IO-system wiring

A shared subnet (`Node.ConnectToSubnet`) and IO-controller / IO-connector association (`IoController.CreateIoSystem` / `IoConnector.ConnectToIoSystem`) are purely **logical**. They do **not** imply a physical cable or port-to-port topology link. TIA Portal validates that physical topology separately, and IRT / isochronous PROFINET configurations can fail compilation until a real port connection exists.

```csharp
var plcPort = plcInterfaceItem.DeviceItems
    .Select(x => x.GetService<NetworkPort>())
    .FirstOrDefault(p => p != null && p.ConnectedPorts.Count == 0);

var drivePort = driveInterfaceItem.DeviceItems
    .Select(x => x.GetService<NetworkPort>())
    .FirstOrDefault(p => p != null && p.ConnectedPorts.Count == 0);

if (plcPort == null || drivePort == null)
{
    throw new InvalidOperationException(
        "Cannot create the physical topology link because an unconnected external NetworkPort could not be resolved.");
}

plcPort.ConnectToPort(drivePort);
```

**Key points:**
- Wire both layers when needed: logical subnet / IO-system membership **and** physical port topology.
- On multi-port devices, one port can already report a connection because of the device's internal switch. Pick the external port with `ConnectedPorts.Count == 0`, not merely the first one returned.
- Compare port proxies with `.Equals(...)`, not `ReferenceEquals(...)`, when checking whether two `NetworkPort` references represent the same underlying port.

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `GetService<NetworkPort>()` | Retrieve network port from a device item |
| `NetworkPort.ConnectedPorts` | Get ports connected to this port |
| `NetworkPort.DisconnectFromPort(port)` | Disconnect a port link |
| `NetworkPort.ConnectToPort(port)` | Connect two ports |
| `GetService<NetworkInterface>()` | Access PROFINET interface |
| `NetworkInterface.Nodes[].SetAttribute()` | Configure IP, subnet, device name |
| `NetworkInterface.IoControllers[].IoSystem` | Walk to connected IO systems |
| `IoSystem.ConnectedIoDevices` | List devices on an IO system |

## Related Files

- [`drive-objects`](../drive-objects/SKILL.md) — SINAMICS devices found through network traversal expose DriveObjectContainer
- [`hardware-and-modules`](../hardware-and-modules/SKILL.md) — hardware modules contain the network ports for DriveCliq wiring
- [`telegrams`](../telegrams/SKILL.md) — telegram addressing depends on the network topology and IO system assignment
- [`safety-commissioning`](../safety-commissioning/SKILL.md) — PROFIsafe safety telegrams require PROFINET network configuration

## Exception Handling

- `GetService<NetworkPort>()` returns `null` for device items without a network port. Filter with `.Where(x => x != null)`.
- `GetService<NetworkInterface>()` returns `null` for non-PROFINET interfaces. Always validate before accessing `.Nodes`.
- `ConnectToPort()` fails if ports are incompatible or already connected. Check `ConnectedPorts` before connecting.
- `DisconnectFromPort()` throws if the port is not currently connected. Verify with `ConnectedPorts.Any()` first.
- `ConnectToSubnet()` / `ConnectToIoSystem()` throw if the link already exists — guard with `ConnectedSubnet == null` / a try-catch, same as `ConnectToPort`.
- `CreateAndConnectToSubnet(name)` / `CreateIoSystem(name)` do **not** throw if a same-named subnet/IO-system already exists elsewhere in the project — they silently return/attach to the existing one. Always scope names to the PLC/device identity (see the naming warning above) rather than relying on an exception to catch collisions.
- PROFINET `SetAttribute()` with an invalid IP address format throws `EngineeringException`. Validate the IP string before setting.
