---
name: crash-diagnosis
description: Diagnosing hard crashes in TIA Portal when called via the Openness API over .NET Remoting IPC. Use when a TIA Portal process dies unexpectedly during an Openness API call sequence, when breadcrumb-based crash localization is needed, or when the suspected crash site does not reproduce in isolation.
metadata:
  siemens-depends-on: "openness-base, engineering-objects"
---

# Crash Diagnosis

## Overview

When TIA Portal crashes hard (access violation or unhandled server-side exception) during an Openness API call, the client does not see an exception immediately. The IPC channel goes silent, the client blocks waiting for a response, and only the **next** API call receives a `CommunicationObjectFaultedException`, `RemotingException`, or similar channel error. The call that appears to fail is almost never the real crash site.

---

## 1. How TIA Portal Openness IPC Works (Crash Context)

The Openness API uses **.NET Remoting over a named-pipe IPC channel** between the client process and the TIA Portal server process. Each API call crosses the channel synchronously.

> **The exception the client sees is NOT thrown by the call that killed TIA Portal. It is thrown by the next call that tries to use the now-dead channel.**

A typical crash sequence:

```
Call N-1:  GetService<SomeDriveService>()          ← TIA Portal dies here (server-side)
		   [IPC channel goes silent]
Call N:    someOtherCall()                          ← client blocks, then gets channel error
		   [client raises ObjectDisposedException / RemotingException]
```

Everything written between N-1 and N was written **post-mortem** — TIA Portal was already dead.

---

## 2. Breadcrumb Logging Rules

To correctly isolate the crash site with a breadcrumb log file:

1. **Append, never overwrite.** `File.WriteAllText` means post-mortem writes keep overwriting the real crash entry. Use `File.AppendAllText` so the full call sequence is preserved.
2. **Clear at run start.** Delete or truncate the file at the beginning of each run so entries from a previous crash do not pollute the analysis.
3. **Write before AND after each suspected call.** The pair `BEFORE: call` / `RETURNED: result` creates a bracket. The crash is in the call whose `BEFORE` line exists but whose `RETURNED` line is absent.
4. **Include object type and path in every entry.** Log `obj.GetType().FullName` and the traversal path so the exact object and its position in the tree are clear.

```csharp
// Correct breadcrumb pattern
File.AppendAllText(path, $"[{DateTime.Now:HH:mm:ss.fff}] {methodName} on {obj.GetType().FullName} at '{treePath}'\n");
var result = theCall();
File.AppendAllText(path, $"[{DateTime.Now:HH:mm:ss.fff}] RETURNED {(result == null ? "null" : result.GetType().FullName)}\n");
```

---

## 3. Reading the Breadcrumb After a Crash

Scan the file for the **last unpaired entry**: a `BEFORE` line that has no following `RETURNED` line before the next call line or end-of-file.

```
[15:44:01.120] GetService<...SomeDriveService>() on DeviceItemImpl at 'Station/PM G120C'
			   ↑ no RETURNED line follows → THIS is the actual crash site
[15:44:01.350] GetService<...OtherService>() on DeviceItemImpl at 'Station/PM G120C'
[15:44:01.410] RETURNED null    ← written post-mortem after IPC timed out; ignore for attribution
```

Everything written **after the unpaired entry** was written post-mortem and must be ignored for crash attribution.

---

## 4. Reproducing a Crash in Isolation

A crash that occurs inside a full traversal **may not reproduce** when the suspected call is made in isolation. Common reasons:

- **Prior call sequence primes internal TIA Portal state.** Some server-side objects are lazily initialized on first access; a preceding call activates a code path that a cold direct call does not trigger.
- **Order dependency in `GetServiceInfos()` + `GetService()`.** `GetServiceInfos()` enumerates available services and may register internal descriptors server-side. Calling `GetService<T>()` without a preceding `GetServiceInfos()` on the same object skips that registration and may silently return `null` instead of crashing — making the isolated repro appear healthy.

To create a valid minimal repro:
1. Walk the **full device tree** in the same depth-first order as the original code.
2. For each object, call `GetServiceInfos()` first, then `GetService()` for **each service in the returned list in order**, then `GetAttributeInfos()` + `GetAttribute()` for each returned service object.
3. Use the append-mode breadcrumb to find the unpaired entry.

Calling only the single suspected service on the suspected object, without the preceding traversal, is **not** a valid repro.

---

## 5. Confirmed Root Cause Pattern (TIA V21 Example)

**Bug observed in TIA V21:** Calling `GetAttribute("IsBuiltIn")` on a service object obtained from a drive `DeviceItem` (e.g. `GsdExportProvider`, `ModuleDescriptionUpdater`) causes TIA Portal to crash server-side:

```
System.NotSupportedException: Mapping error: Expected type 'System.String', but was 'System.Boolean'.
```

The attribute is `Boolean` in TIA Portal but the Openness mapper descriptor declares it as `String` — a TIA Portal bug that affects every service that exposes `IsBuiltIn` on those drive module types. The client sees the channel error only on the **next** IPC call. Switching the breadcrumb from `WriteAllText` to `AppendAllText` reveals the actual unpaired entry.

---

## 6. V21 empirical case: G120C bulk attribute options

An observed TIA Portal V21 device-specific hard crash occurs when `GetAttributes(AttributeAccessOptions)` is called on a SINAMICS **G120C**. Use the per-name `GetAttributes(names)` snapshot pattern instead for that device family.

This observation was not independently reproduced in this session. Do **not** generalize it to other device families or add a broader exclusion unless the unpaired-breadcrumb and full-traversal evidence standard below is met.

---

## 7. Skip Strategies After a Crash Is Confirmed

Once a crash site is confirmed via the append-mode breadcrumb, add an entry to the appropriate skip list. **Never add entries speculatively** — only after the unpaired breadcrumb is proven to be the real crash site.

### 7a. Attribute-Level Skip

Skip a named attribute on all objects (wildcard `"*"`) or only on objects whose type name contains a given fragment:

```csharp
// Format: (typeNameFragment, attributeName)
// "*" as typeNameFragment skips on every object type.
private static readonly (string TypeFragment, string AttributeName)[] _crashRiskAttributes =
{
	("*", "IsBuiltIn"),  // crashes on service objects on certain drive DeviceItems;
						  // wildcard is safe — IsBuiltIn is a legitimate boolean attribute
						  // but the Openness mapper erroneously declares it as String.
};
```

The check runs **before** `GetAttribute` is called, so the IPC call is never made.

### 7b. Service-Level Unconditional Skip

Skip a service type entirely on every object. Use only when the service crashes on **any** device, not just a specific family:

```csharp
// Type name substring match (case-insensitive). The GetService() call is never made.
private static readonly string[] _crashRiskServiceNameFragments =
{
	"mrpdomain",
	"sivarc",
};
```

### 7c. Service-Level Conditional Skip

Skip a service type only when the **current traversal path** also contains a given fragment. Use when the crash is device-family-specific to avoid over-broad skipping on healthy devices:

```csharp
// Format: (serviceTypeFragment, pathFragment)
// Service is skipped only when BOTH the service type name AND the current tree path match.
private static readonly (string ServiceFragment, string PathFragment)[] _conditionalCrashRiskServices =
{
	// Example: service crashes only on a specific drive module type, not on standard CPUs.
	("CommunicationManagement", "PM G120C"),
};
```

The path check uses `IndexOf(..., OrdinalIgnoreCase)` against the slash-delimited tree path accumulated during traversal.

### Evidence Standard Before Adding Any Entry

All three must be confirmed:
1. An unpaired `BEFORE` line exists in the **append-mode** breadcrumb — the `RETURNED` line is absent.
2. The crash reproduces with the **full tree-walk repro** (not an isolated single call).
3. The unpaired entry is the **last** unpaired BEFORE-without-RETURNED in the file — entries after it are post-mortem noise.

---

## 8. Checklist Before Reporting a Crash

- [ ] Breadcrumb is in **append mode** and was **cleared at run start**.
- [ ] The **unpaired entry** (BEFORE with no RETURNED) is identified — not just the last entry in the file.
- [ ] The crash was **reproduced** with a repro that replicates the full call sequence (not just the single suspected call in isolation).
- [ ] The TIA Portal **stack trace** from the Windows Error Report or ADIAG is attached — it shows the server-side call chain and the exact mapper/attribute failure.
- [ ] The report states: object type, service type, device type, and the sequence of preceding calls that prime the crash state.

---

## Quick Reference

| Rule | Detail |
|---|---|
| Real crash site | Last `BEFORE` line without a following `RETURNED` line |
| Post-mortem entries | All lines after the unpaired entry — ignore for attribution |
| Breadcrumb mode | `File.AppendAllText` — never `File.WriteAllText` |
| Isolated repro is invalid | Must replicate full call sequence including `GetServiceInfos()` + ordering |
| Skip-list entry evidence | Unpaired breadcrumb entry + full-traversal repro — never speculative |
| G120C attribute snapshot | Use per-name `GetAttributes(names)`; do not generalize the observed V21 options-overload crash |

## Quick Reference — Known V21 Instance-Killing Traps

| Trap | Symptom | Fix |
|---|---|---|
| `TiaPortalProcess.Dispose()` on a handle from `GetProcesses()` | Live TIA Portal instance dies unexpectedly (e.g. during a "refresh process list" action) | Never dispose handles from `GetProcesses()` — only your own `GetCurrentProcess()` handle is safe to dispose. See [`session-and-project`](../session-and-project/SKILL.md). |
| Background Openness thread created as STA | Attach/open call hangs indefinitely with no exception | Background/worker threads must be `ApartmentState.MTA` — an STA thread with no message pump stalls the Remoting handshake. See [`threading-and-concurrency`](../threading-and-concurrency/SKILL.md). |

## Related Files

- [`engineering-objects`](../engineering-objects/SKILL.md) — `GetServiceInfos()` / `GetService()` call ordering, `GetAttributeInfos()` / `GetAttribute()` patterns
- [`object-tree-walking`](../object-tree-walking/SKILL.md) — schema-free traversal, cycle prevention, service enumeration
- [`session-and-project`](../session-and-project/SKILL.md) — `TiaPortalProcess.Dispose()` instance-killing trap when called on `GetProcesses()` handles
- [`threading-and-concurrency`](../threading-and-concurrency/SKILL.md) — STA-without-message-pump stalls on background Openness worker threads
