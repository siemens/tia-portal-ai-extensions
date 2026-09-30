---
name: drive-control-charts
description: Drive Control Charts (DCC) for TIA Portal Openness. Use when creating, importing, exporting DCC charts, managing blocks, pins, parameters, and configuring drive functions graphically.
metadata:
  siemens-depends-on: "openness-base, drive-objects"
---

# Drive Control Charts (DCC)

## Overview

Drive Control Charts (DCC) provide a graphical programming method for configuring and parameterizing Siemens drives within TIA Portal. The DCC API enables developers to programmatically create, modify, import, and export drive control charts, blocks, pins, and parameters using the TIA Portal Openness SDK.

DCC simplifies drive commissioning by allowing engineers to visually represent drive functions and their interconnections through blocks, signals, and parameters. The API supports full lifecycle management of DCC artifacts, from chart creation to parameter binding.

## Required Namespaces

```csharp
using Siemens.Engineering.MC.Drives;
using Siemens.Engineering.MC.Drives.Dcc;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.DCC.dll`
- `Siemens.Engineering.Startdrive.dll`

## Common Patterns

### Accessing DriveObjectContainer and DriveControlChartContainer

**Description:**
Retrieve the `DriveObjectContainer` from an axis device item, then access the `DriveControlChartContainer` to obtain the collection of DCC charts associated with a drive object.

**Example:**
```csharp
var device = Project.Devices.First(x => x.Name.Contains("S120Democase"));
var axis = device.DeviceItems.First(x => x.Name.Contains("BlueAxis"));
var driveObjectContainer = axis.GetService<DriveObjectContainer>();
var driveObject = driveObjectContainer.DriveObjects.First();
var chartContainer = driveObject.GetService<DriveControlChartContainer>();
var charts = chartContainer.Charts;
```

**Key Types and Methods:**
- `DriveObjectContainer` — container for drive objects within a device item
- `DriveObjectContainer.DriveObjects` — collection of drive objects
- `DriveControlChartContainer` — container providing access to DCC charts
- `DriveControlChartContainer.Charts` — collection of `DriveChart` instances

### Importing DCC Charts

**Description:**
Import an existing DCC file (`.dcc`) into the project's drive chart collection. Supports conflict resolution strategies via `DccImportOptions`.

**Example:**
```csharp
var dccCharts = device.DeviceItems.First(x => x.Name.Contains("BlueAxis"))
    .GetService<DriveObjectContainer>()
    .DriveObjects
    .First().GetService<DriveControlChartContainer>().Charts;

dccCharts.Import(importDccPath.ToString(), DccImportOptions.RenameOnConflict);
```

**Key Types and Methods:**
- `DriveChartCollection.Import(string path, DccImportOptions options)` — imports a DCC file
- `DccImportOptions.RenameOnConflict` — enum value to automatically rename conflicting chart names

### Exporting DCC Charts

**Description:**
Export a single DCC chart to a `.dcc` file on disk for reuse or sharing.

**Example:**
```csharp
dccCharts.Single(c => c.Name == "DCC_Example").Export(exportDccPath.FullName);
```

**Key Types and Methods:**
- `DriveChart.Export(string path)` — exports the chart to the specified file path

### Creating a DCC Chart

**Description:**
Create a new, empty DCC chart programmatically by name.

**Example:**
```csharp
var chart = chartContainer.Charts.Create("NewChartFromCode");
```

**Key Types and Methods:**
- `DriveChartCollection.Create(string name)` — creates a new chart with the given name

### Creating DCC Blocks

**Description:**
Add a functional block (e.g., `ADD`, `MUL`, `SEL`) to an existing DCC chart.

**Example:**
```csharp
var dccBlock1 = chart.Blocks.Create("ADD");
```

**Key Types and Methods:**
- `DriveChart.Blocks` — property providing access to the block collection of a chart
- `DriveBlockCollection.Create(string blockTypeName)` — creates a block of the specified type

### Publishing DCC Pins

**Description:**
Publish a block pin to a specific parameter address, enabling signal routing between DCC blocks and drive parameters.

**Example:**
```csharp
var pin = dccBlock1.Pins.First(x => x.Name.Equals("X1"));
pin.Publish(true, 21500);
```

**Key Types and Methods:**
- `DriveBlock.Pins` — collection of pins belonging to a block
- `DrivePin.Publish(bool direction, int parameterAddress)` — publishes the pin to a parameter; `direction` controls input/output routing

### Accessing and Interconnecting DCC Parameters

**Description:**
Find drive parameters by their identifier and establish interconnections by assigning one parameter's value to another.

**Example:**
```csharp
var dccParameter = driveObject.Parameters.Find("p21500");
var parameterToConnect = driveObject.Parameters.Find("r21");
dccParameter.Value = parameterToConnect;
```

**Key Types and Methods:**
- `DriveObject.Parameters` — collection of parameters associated with a drive object
- `DriveParameterCollection.Find(string identifier)` — locates a parameter by its name (e.g., `"p21500"`, `"r21"`)
- `DriveParameter.Value` — property to get or set the parameter value, enabling interconnections

## Quick Reference

| Method / Pattern | Purpose |
|------------------|---------|
| `axis.GetService<DriveObjectContainer>()` | Access drive objects from an axis device item |
| `driveObject.GetService<DriveControlChartContainer>()` | Access the DCC chart container for a drive object |
| `chartContainer.Charts` | Retrieve the collection of DCC charts |
| `DriveChartCollection.Import(path, options)` | Import a `.dcc` file into the chart collection |
| `DriveChart.Export(path)` | Export a chart to a `.dcc` file |
| `DriveChartCollection.Create(name)` | Create a new DCC chart by name |
| `DriveChart.Blocks.Create(blockType)` | Create a functional block within a chart |
| `DrivePin.Publish(direction, address)` | Publish a pin to a parameter address |
| `DriveParameterCollection.Find(id)` | Locate a parameter by identifier |
| `DriveParameter.Value` | Get or set a parameter's value for interconnection |

## Related Files

- [`drive-objects`](../drive-objects/SKILL.md) — core access patterns for DriveObject and DriveFunctionInterface
- [`parameters`](../parameters/SKILL.md) — parameter access and BiCo wiring through DriveObject.Parameters
- [`safety-commissioning`](../safety-commissioning/SKILL.md) — safety configuration via DriveFunctionInterface.SafetyCommissioning
- [`telegrams`](../telegrams/SKILL.md) — telegram management on DriveObject.Telegrams
- [`hardware-and-modules`](../hardware-and-modules/SKILL.md) — hardware module insertion, type changes, and hardware catalog

## Exception Handling

When working with DCC APIs, handle the following exceptions:

- **`DccException`** — base exception for general DCC-related errors (e.g., invalid chart operations, unsupported block types)
- **`DccImportException`** — thrown when a DCC file import fails (e.g., corrupted file, version mismatch, missing dependencies)
- **`DccExportException`** — thrown when a DCC file export fails (e.g., insufficient permissions, invalid path)

**Best practice:** Wrap DCC operations in try-catch blocks, especially for file I/O and parameter resolution:

```csharp
try
{
    dccCharts.Import(importPath, DccImportOptions.RenameOnConflict);
}
catch (DccImportException ex)
{
    // Handle import failure: log error, retry with different options, or abort
}
catch (DccException ex)
{
    // Handle general DCC errors
}
```

Always validate parameter identifiers and file paths before invoking DCC methods to minimize runtime exceptions.
