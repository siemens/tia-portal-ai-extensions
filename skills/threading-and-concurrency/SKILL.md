---
name: threading-and-concurrency
description: Thread-safety and apartment model rules for TIA Portal Openness. Use when building multi-threaded Openness apps, background services, or MCP-style servers that receive concurrent calls, or when hitting cross-thread exceptions.
metadata:
  siemens-depends-on: "openness-base"
---

# Threading and Concurrency

## Overview

Openness objects are **not inherently thread-safe** — the SDK performs no locking for you. Every proxy object belongs to the thread that created or attached its `TiaPortal` instance. TIA Portal itself also runs every operation **one after another**, regardless of how many threads or apps call into it. Understanding these two facts is required before adding any multi-threading to an Openness application.

## Required Namespaces

```csharp
using Siemens.Engineering;
```

## Common Patterns

### Objects Are Bound to the Creating/Attaching Thread

**Description:** A proxy object is tied to the thread that created or attached the `TiaPortal` instance it came from. If the `TiaPortal` instance was created or attached on an STA (Single-Threaded Apartment) thread, every associated Openness object must be accessed **from that same STA thread**. Accessing it from another thread throws an exception.

**Anti-pattern:**

```csharp
// Wrong: creating TiaPortal on the UI (STA) thread, then touching its objects from a worker thread
TiaPortal portal = new TiaPortal(TiaPortalMode.WithUserInterface); // created on STA thread
Task.Run(() => portal.Projects[0].Name); // throws — cross-thread access
```

**Correct pattern:**

```csharp
// Marshal the call back onto the owning (STA) thread, e.g. via a dispatcher/synchronization context
await dispatcher.InvokeAsync(() => portal.Projects[0].Name);
```

**Key points:**
- Serialize your own access to shared Openness objects when several threads might touch the same project.
- Never pass a proxy object to another thread without first ensuring that thread is the one that owns it (or is compatible, see MTA below).

### 🛑 Background/worker threads MUST be MTA — an STA background thread has no message pump

**Description:** If a `TiaPortal` instance is created or attached on a **background** thread (not the UI thread) — e.g. inside a Windows Service, a headless worker, or a background thread spun up from a WPF app for attach/open logic — that thread **must** be `ApartmentState.MTA`. An STA background thread has no COM message pump running (unlike the UI thread, which pumps messages via its dispatcher loop), and the .NET Remoting handshake used by Openness IPC silently stalls waiting for that pump, hanging the operation. This is easy to miss because it is *correct* to use STA for a foreground UI thread — the requirement is specifically about threads that do not run a UI message loop.

```csharp
// WRONG — background thread with default/explicit STA has no message pump; Openness attach/IPC stalls
var thread = new Thread(() => AttachToTiaPortal());
thread.SetApartmentState(ApartmentState.STA); // or omitted on a context that defaults to STA
thread.Start();

// CORRECT — background Openness worker threads must be MTA
var thread = new Thread(() => AttachToTiaPortal());
thread.SetApartmentState(ApartmentState.MTA);
thread.Start();
thread.Join();
```

**Key points:**
- This is the single most common Openness threading trap in WPF apps: the main UI thread is STA by default, and it's easy to assume a background helper thread should match — it should not.
- If a background Openness thread appears to hang indefinitely on attach/open (no exception, no progress), suspect STA-without-message-pump before anything else.

### Prefer an MTA Thread When Multi-Threading for Performance

**Description:** If you introduce multi-threading purely to parallelize your **own** application logic (not to speed up TIA Portal itself), create the `TiaPortal` instance on a Multi-Threaded Apartment (MTA) thread rather than an STA thread. This avoids the strict single-thread affinity that STA-created instances impose.

**Example:**

```csharp
var thread = new Thread(() =>
{
    TiaPortal portal = new TiaPortal(TiaPortalMode.WithoutUserInterface);
    // Openness work here
});
thread.SetApartmentState(ApartmentState.MTA);
thread.Start();
thread.Join();
```

**Key points:**
- An MTA thread only helps your own orchestration (e.g. queuing, I/O overlap) — it does **not** make TIA Portal execute operations in parallel.
- Console apps default to MTA; WPF/WinForms UI threads default to STA — be explicit about which apartment your Openness session runs on.

### No Parallel Execution Inside TIA Portal

**Description:** TIA Portal processes every operation — GUI actions and Openness calls alike — strictly one after another, even across multiple Openness apps and multiple threads calling into the same instance. Threads only overlap your own application's work; they never make TIA Portal itself execute faster in parallel.

**Key points:**
- Do not expect throughput gains from firing many Openness calls concurrently at the same TIA Portal instance — they will be serialized internally regardless.
- Design concurrency (e.g. a work queue) around this serialization rather than fighting it — see the queuing pattern in [`performance-and-caching`](../performance-and-caching/SKILL.md) for batching reads/writes instead of parallelizing them.

## Quick Reference

| Rule | Consequence |
|---|---|
| Proxy bound to creating/attaching thread | STA-created objects must be accessed from that same STA thread only |
| Background/worker thread must be MTA | An STA background thread has no message pump — Openness IPC handshake stalls; only foreground UI threads should stay STA |
| SDK does no locking | Serialize your own access to shared objects across threads |
| MTA for own multi-threading | Use MTA when threading is for your app's performance, not TIA Portal's |
| TIA Portal is single-op-at-a-time | No parallel speedup inside TIA Portal, regardless of thread/app count |
| Cross-thread access | Throws an exception — always marshal back to the owning thread |

## Related Files

- [`performance-and-caching`](../performance-and-caching/SKILL.md) — caching and batching strategies that combine well with a single-writer threading model
- [`engineering-objects`](../engineering-objects/SKILL.md) — `ExclusiveAccess`/`Transactions`, which also apply per-session regardless of threading model
- [`session-and-project`](../session-and-project/SKILL.md) — creating and attaching `TiaPortal` instances

## Exception Handling

- Accessing an Openness object from a thread other than its owning thread throws an exception — catch and marshal the call back to the correct thread instead of retrying blindly.
- Do not assume retrying a cross-thread call on the same (wrong) thread will succeed; the fix is always to invoke on the owning thread.
