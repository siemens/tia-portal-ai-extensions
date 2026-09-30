---
name: change-detection
description: Detecting what changed in a TIA Portal project via Openness. Use when comparing project state over time, deciding whether a re-download/re-compile is needed, tracking library type versions, or checking if a PLC program or Safety configuration changed.
metadata:
  siemens-depends-on: "openness-base, engineering-objects"
---

# Change Detection

## Overview

Openness offers no single "diff" API. Instead, several targeted services and properties each answer a narrower question about *what* changed. Pick the right one for the question you're actually asking instead of re-reading and comparing the whole project.

## Required Namespaces

```csharp
using Siemens.Engineering;
using Siemens.Engineering.CrossReference;
```

## Common Patterns

### Choose the Right Change-Detection Service

**Description:** Match the question you need answered to the corresponding service or property. Re-reading and diffing an entire project tree is expensive (see [`performance-and-caching`](../performance-and-caching/SKILL.md)) — these services are purpose-built to be cheap and precise.

| What you want to know | Use this | Detail |
|---|---|---|
| Is it the same object as seen last time? | `ObjectIdentifierProvider` | Each object has a stable, project-unique ID (see [`performance-and-caching`](../performance-and-caching/SKILL.md)) |
| Did a library type change? | GUID + version | Each library type and version has its own globally unique GUID |
| Did the project change at all? | `ProjectBase` timestamps | `CreationTime` and `LastModified` (last save) |
| Did an object change at all? | `CreationDate` / `ModifiedDate` | Many project objects expose these properties (last edit) |
| Did the PLC program change at all? | `PlcChecksumProvider` | Checksum changes on edits; empty until fully compiled, resets to empty on program change until next compile |
| What exactly changed in Safety? | `SafetySignatureProvider` | Multiple, granular F-signatures for Safety administration and program blocks |
| What exactly changed in a block or PLC data type? | `FingerprintProvider` | Fingerprints for code, interface, properties, comments and more, on program blocks and PLC data types |
| Where is an object used? | `CrossReferenceService` | Context such as unused, using, and used-by — see [`blocks`](../blocks/SKILL.md) for the full pattern |
| What does a library type or master copy bring along? | `LibraryTypeVersion` / `MasterCopy` | `Dependencies`, `Dependants`, `MasterCopiesContainingInstances` on a `LibraryTypeVersion`; `ContentDescriptions` on a `MasterCopy` — see [`global-library`](../global-library/SKILL.md) |

### Check the PLC Program Checksum

**Description:** `PlcChecksumProvider` exposes a checksum that changes whenever the compiled PLC program changes. It is empty until the software has been fully compiled at least once, and resets to empty on further edits until the next compile.

**Example:**

```csharp
PlcChecksumProvider checksumProvider = plcSoftware.GetService<PlcChecksumProvider>();
string checksum = checksumProvider.Checksum;
if (string.IsNullOrEmpty(checksum))
{
    // Not compiled yet, or changed since last compile — trigger ICompilable.Compile() first
}
```

**Key Types and Methods:**
- `PlcChecksumProvider` — service on `PlcSoftware`
- `PlcChecksumProvider.Checksum` — empty when not (yet) compiled or when the program changed since the last compile

### Check Fine-Grained Block/UDT Fingerprints

**Description:** `FingerprintProvider` exposes separate fingerprints for different aspects of a block or PLC data type (code, interface, properties, comments, etc.), letting you detect exactly *what part* changed instead of only *whether* something changed.

**Example:**

```csharp
FingerprintProvider fingerprintProvider = block.GetService<FingerprintProvider>();
string interfaceFingerprint = fingerprintProvider.InterfaceFingerprint;
string codeFingerprint = fingerprintProvider.CodeFingerprint;
```

**Key Types and Methods:**
- `FingerprintProvider` — service available on program blocks and PLC data types
- Exposes separate fingerprints per aspect (code, interface, properties, comments, ...)

### Check Safety Signatures

**Description:** `SafetySignatureProvider` exposes multiple, granular F-signatures used for Safety administration and Safety program blocks, allowing precise change tracking in Safety-relevant parts of a project.

**Key Types and Methods:**
- `SafetySignatureProvider` — service exposing F-signatures for Safety administration and program blocks

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `ObjectIdentifierProvider` | Confirm the same object across sessions |
| GUID + version on a library type | Detect library type changes |
| `ProjectBase.CreationTime` / `LastModified` | Detect any project-level change |
| `CreationDate` / `ModifiedDate` | Detect any object-level change |
| `PlcChecksumProvider.Checksum` | Detect PLC program change (compile-state aware) |
| `SafetySignatureProvider` | Detect Safety-specific changes via F-signatures |
| `FingerprintProvider` | Detect fine-grained block/UDT changes (code, interface, comments, ...) |
| `CrossReferenceService.GetCrossReferences()` | Find where an object is used |

## Related Files

- [`blocks`](../blocks/SKILL.md) — `CrossReferenceService` usage pattern in full
- [`global-library`](../global-library/SKILL.md) — `LibraryTypeVersion` dependency/dependant tracking
- [`performance-and-caching`](../performance-and-caching/SKILL.md) — `ObjectIdentifierProvider` for stable re-fetch, and why avoiding full re-reads matters
- [`plc-safety-administration`](../plc-safety-administration/SKILL.md) — Safety administration context for `SafetySignatureProvider`

## Exception Handling

- `GetService<T>()` for these providers throws if the object does not support that service — check object classification (e.g. only `PlcSoftware` supports `PlcChecksumProvider`) before requesting it.
- A `PlcChecksumProvider.Checksum` of empty string is a valid state (not-yet-compiled or changed-since-compile), not an error — do not treat it as a failure.
