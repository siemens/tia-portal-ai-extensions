---
name: telegrams
description: Telegrams for data exchange between SINAMICS drives and PLC. Use when configuring main telegrams, safety telegrams, changing telegram numbers, resizing telegram I/O, and inserting PROFIsafe telegrams.
metadata:
  siemens-depends-on: "openness-base, drive-objects"
---

# Telegrams

## Overview

Telegrams define the data exchange between SINAMICS drives and the PLC. Main telegrams carry process data (inputs/outputs), while safety telegrams carry failsafe signals (e.g., STW/STA for PROFIsafe). The `Telegrams` collection on a `DriveObject` supports querying by type, changing telegram numbers, resizing input/output lengths, and inserting new safety telegrams.

## Required Namespaces

```csharp
using System.Linq;
using Siemens.Engineering;
using Siemens.Engineering.MC.Drives;
using Siemens.Engineering.MC.Drives.Enums;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`
- `Siemens.Engineering.Startdrive.dll`

## Common Patterns

### Get Telegram by Type

**Description:** Query the `Telegrams` collection filtered by `TelegramType` enum. Use `TelegramType.SafetyTelegram` for failsafe telegrams and `TelegramType.MainTelegram` for process data.

**Example:**

```csharp
var safetyTelegram = driveObjectContainer.DriveObjects.First().Telegrams
    .First(x => x.Type == TelegramType.SafetyTelegram);

var mainTelegram = driveObject.Telegrams
    .First(x => x.Type == TelegramType.MainTelegram);
```

**Key Types and Methods:**
- `DriveObject.Telegrams` — collection of all telegrams on the drive object
- `TelegramType.SafetyTelegram` — enum value for failsafe telegrams
- `TelegramType.MainTelegram` — enum value for process data telegrams

### Set Telegram Attributes (Failsafe)

**Description:** Configure safety telegram attributes such as destination address and monitoring time via `SetAttribute()`.

**Example:**

```csharp
safetyTelegram.SetAttribute("Failsafe_FDestinationAddress", 10);
safetyTelegram.SetAttribute("Failsafe_ManualAssignmentFMonitoringtime", true);
safetyTelegram.SetAttribute("Failsafe_FMonitoringtime", 100);
```

**Key Types and Methods:**
- `Telegram.SetAttribute(name, value)` — set a named attribute on the telegram
- `Failsafe_FDestinationAddress` — PROFIsafe destination address
- `Failsafe_FMonitoringtime` — PROFIsafe monitoring time in milliseconds

### Change Main Telegram Number

**Description:** Assign a new telegram number to a main telegram directly via the `TelegramNumber` property.

**Example:**

```csharp
mainTelegram.TelegramNumber = 20;
```

**Key Types and Methods:**
- `Telegram.TelegramNumber` — property holding the telegram number (read/write)

### Read Telegram Address (StartAddress)

**Description:** Retrieve the start address of a telegram's address block(s). Useful for correlating telegrams with technology object input addresses.

**Example:**

```csharp
var address = telegrams?.FirstOrDefault(
    x => x.Type == TelegramType.MainTelegram)
    ?.Addresses.FirstOrDefault();

var startAddress = (int)telegram.Addresses[0].GetAttribute("StartAddress");
```

🛑 **When a telegram has both input and output address blocks, `Addresses[0]`/`Addresses[1]` positional indexing is unreliable** — it can return the same `StartAddress` for both directions. Filter by direction instead (`Address.IoType == AddressIoType.Input`/`.Output`) whenever you need input vs. output specifically, such as when connecting a Technology Object to its drive axis — see [`technology-objects`](../technology-objects/SKILL.md).

**Key Types and Methods:**
- `Telegram.Addresses` — collection of address blocks on the telegram
- `Address.GetAttribute("StartAddress")` — retrieves the starting I/O address
- `Address.IoType` — filter by `AddressIoType.Input`/`.Output` instead of indexing when direction matters

### Insert Safety Telegram

**Description:** Check if a safety telegram can be inserted, then insert it with `InsertSafetyTelegram()`. Always validate with `CanInsertSafetyTelegram()` first.

**Example:**

```csharp
if (telegrams.CanInsertSafetyTelegram(30))
{
    telegrams.InsertSafetyTelegram(30);
}
```

**Key Types and Methods:**
- `Telegrams.CanInsertSafetyTelegram(number)` — validates whether the telegram number is available
- `Telegrams.InsertSafetyTelegram(number)` — creates the safety telegram

### Validate and Change Telegram Number

**Description:** Validate telegram changeability before assigning a new telegram number to avoid conflicts.

**Example:**

```csharp
if (mainTelegram.CanChangeTelegram(999))
{
    mainTelegram.TelegramNumber = 999;
}
```

**Key Types and Methods:**
- `Telegram.CanChangeTelegram(number)` — returns `true` if the change is valid
- `Telegram.TelegramNumber` — property to assign the new number

### Change Telegram Size

**Description:** Resize the input or output length of a main telegram. Specify direction, new length, and whether to preserve data.

**Example:**

```csharp
mainTelegram.ChangeSize(AddressIoType.Input, 10, false);
```

**Key Types and Methods:**
- `Telegram.ChangeSize(direction, length, preserveData)` — resize method
- `AddressIoType.Input` / `AddressIoType.Output` — direction of the data block
- `preserveData` — `true` to keep existing data during resize

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `Telegrams.First(x => x.Type == TelegramType.SafetyTelegram)` | Get safety telegram |
| `Telegrams.First(x => x.Type == TelegramType.MainTelegram)` | Get main telegram |
| `Telegram.SetAttribute(name, value)` | Configure safety telegram attributes |
| `Telegram.TelegramNumber = 20` | Change telegram number |
| `Addresses[0].GetAttribute("StartAddress")` | Read telegram start address |
| `Telegrams.CanInsertSafetyTelegram(number)` | Validate safety telegram insertion |
| `Telegrams.InsertSafetyTelegram(number)` | Insert new safety telegram |
| `Telegram.CanChangeTelegram(number)` | Validate telegram number change |
| `Telegram.ChangeSize(direction, length, preserveData)` | Resize telegram I/O length |

## Related Files

- [`drive-objects`](../drive-objects/SKILL.md) — obtaining `DriveObject` to access its `Telegrams` collection
- [`networks-and-drivecliq`](../networks-and-drivecliq/SKILL.md) — network topology affects telegram addressing
- [`safety-commissioning`](../safety-commissioning/SKILL.md) — safety telegrams are required for PROFIsafe functions (STO, SImO)
- [`parameters`](../parameters/SKILL.md) — parameter-based configuration interacts with telegram data mapping

## Exception Handling

- `Telegrams.First(...)` throws `InvalidOperationException` if no telegram of the specified type exists. Use `FirstOrDefault()` with null checks.
- `CanInsertSafetyTelegram()` and `CanChangeTelegram()` return `false` rather than throwing. Always validate before inserting or changing.
- `ChangeSize()` may fail if the requested length exceeds the maximum for the telegram type. Check the return value.
- `SetAttribute()` throws if the attribute name is invalid or the value type is mismatched. Use valid attribute names from the SINAMICS documentation.
