---
name: performance-and-caching
description: Performance design for TIA Portal Openness applications. Use when an app feels slow, when navigating deep object chains in loops, when deciding whether to cache Openness data, or when reading/writing many attributes at once.
metadata:
  siemens-depends-on: "openness-base"
---

# Performance and Caching

## Overview

TIA Portal Openness has **no built-in cache**. Every method call, property get/set, and collection navigation (including indexers like `[0]`) is a live inter-process call to the TIA Portal process, including data serialization and deserialization. Performance is entirely the application's design responsibility: build your own model/cache layer, minimize round-trips, and batch reads and writes.

## Required Namespaces

```csharp
using Siemens.Engineering;
```

## Common Patterns

### Build Your Own Model and Cache Layer

**Description:** Do not read Openness objects directly from UI/business logic on every access. Walk the tree once, copy the data you need into your own plain model classes, and read from that cache afterward. This also decouples your app from Openness type/version changes and lets you translate technical Openness names into user-friendly labels.

**Example:**

```csharp
// Your own lightweight model, populated once
internal sealed class DeviceModel
{
    public string Name { get; init; }
    public string TypeIdentifier { get; init; }
}

List<DeviceModel> CacheDevices(DeviceComposition devices)
{
    var result = new List<DeviceModel>();
    foreach (Device device in devices)
    {
        result.Add(new DeviceModel { Name = device.Name, TypeIdentifier = device.TypeIdentifier });
    }
    return result; // subsequent reads hit this list, not TIA Portal
}
```

**Key points:**
- Read once per session (or per `ExclusiveAccess` window), then serve reads from your own model.
- Build a **top-down** tree cache: don't re-navigate `Parent` when you already came from the parent — hold the reference instead.
- Keep at most **500,000** .NET references to Openness objects (the maximum supported limit).
- Expect high *reported* RAM usage — managed memory is released on the .NET runtime's own GC schedule, not immediately.

### Cache the Navigation Chain — Don't Chain Live Property Access

**Description:** Compositions and associations (e.g. `Projects`, `Devices`) are live too. Every `.` hop and every `[ ]` indexer is its own inter-process round-trip. A single chained expression can fire many live calls; inside a loop over thousands of objects this dominates runtime.

**Anti-pattern:**

```csharp
// One innocent-looking line = many live IPC calls (one per hop / indexer)
string deviceName = tiaPortal.Projects[0].Devices[0].Name;
```

**Correct pattern:**

```csharp
// Cache each step in a local variable, then read once
ProjectComposition projects = tiaPortal.Projects;
Project project = projects[0];
DeviceComposition devices = project.Devices;
Device device = devices[0];
string deviceName = device.Name;
```

**Key points:**
- Hold each composition and object in a local variable; reuse the cached reference instead of re-walking the tree.
- Avoid LINQ over live Openness collections where possible — each enumeration pass re-queries live (faster since V21 for simple LINQ, but still not free).

### Bulk Read/Write with GetAttributes / SetAttributes

**Description:** Reading or writing properties one at a time (`obj.SomeProperty`) issues one live call per property. `GetAttributes()` and `SetAttributes()` read or write many named attributes of an object in a **single** call.

**Example:**

```csharp
// Instead of: name = obj.GetAttribute("Name"); comment = obj.GetAttribute("Comment"); ...
IDictionary<string, object> values = obj.GetAttributes("Name", "Comment", "Author");

// Instead of: obj.SetAttribute("Name", newName); obj.SetAttribute("Comment", newComment);
obj.SetAttributes(new Dictionary<string, object>
{
    ["Name"] = newName,
    ["Comment"] = newComment,
});
```

**Key Types and Methods:**
- `IEngineeringObject.GetAttributes(params string[])` — bulk attribute read in a single round-trip
- `IEngineeringObject.SetAttributes(IDictionary<string, object>)` — bulk attribute write in a single round-trip

### Bulk attribute reads — prefer per-name batching

**Description:** For snapshot-style or inspection-style bulk reads, the safest high-throughput pattern is: discover names with `GetAttributeInfos()`, then issue **one** `GetAttributes(names)` call per object and cache that result **per instance**.

**Recommended pattern:**
- Build the attribute-name list from `GetAttributeInfos()`.
- Batch-read those names with `GetAttributes(names)`.
- Cache the resulting values per object instance and reuse that cache for later attribute lookups.
- If one name faults, fall back only for that name instead of abandoning batching for the whole object.
- Memoize frequently-read basics like `Name` and `TypeIdentifier` on the wrapper instance as a zero-risk optimization.

**Important rules:**
- Do **not** cache attribute-name lists per CLR type. Different instances of the same runtime type can legitimately expose different attribute sets, so a per-type cache is a correctness bug.
- Device-specific hard-crash exclusions and the evidence required before adding them are documented in [`crash-diagnosis`](../crash-diagnosis/SKILL.md); per-name `GetAttributes(names)` remains the recommended snapshot pattern.
- When diagnosing crash-risk services or attributes on specific device families, keep the skip-list / breadcrumb strategy from [`crash-diagnosis`](../crash-diagnosis/SKILL.md) alongside your batching logic.

### Re-fetch Objects Fast — ObjectIdentifierProvider (V21+)

**Description:** `ObjectIdentifierProvider` gives each engineering object a stable, project-unique ID. Use it to re-fetch the same object later — even after closing and reopening the project — instead of re-walking the whole tree to relocate it.

**Example:**

```csharp
ObjectIdentifierProvider idProvider = someObject.GetService<ObjectIdentifierProvider>();
string stableId = idProvider.GetIdentifier();

// ... later, possibly after reopening the project ...
IEngineeringObject sameObject = idProvider.GetObject(stableId, project);
```

**Key Types and Methods:**
- `ObjectIdentifierProvider` — service exposing a stable, project-unique identifier per object
- Available since TIA Portal V21

### Skip the Search Index During Bulk Changes

**Description:** The TIA Portal setting `SearchInProject` builds the in-project search index on every change, behind the GUI. During massive programmatic project changes this adds significant overhead. Disable it for the duration of bulk operations via Openness, or let the user control it.

**Key points:**
- Toggle the setting via Openness before bulk edits and restore it afterward (or leave the choice to the user).
- Re-enabling it triggers a (one-time) index rebuild.

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| Own model/cache classes | Avoid repeated live reads; decouple from Openness types/versions |
| Cache navigation chain in locals | Avoid one live call per `.` hop / `[ ]` indexer |
| `GetAttributes()` / `SetAttributes()` | Bulk read/write many properties in one round-trip |
| `ObjectIdentifierProvider` | Stable ID to re-fetch an object later, even across sessions |
| `SearchInProject` toggle | Disable index building during massive bulk changes |
| 500,000 references | Maximum supported number of live .NET references to Openness objects |

## Related Files

- [`engineering-objects`](../engineering-objects/SKILL.md) — `ExclusiveAccess` and `Transactions`, which should wrap heavy bulk operations
- [`threading-and-concurrency`](../threading-and-concurrency/SKILL.md) — thread-affinity rules that also affect how you structure a cache layer
- [`object-tree-walking`](../object-tree-walking/SKILL.md) — schema-free traversal patterns; combine with caching to walk the tree once
- [`crash-diagnosis`](../crash-diagnosis/SKILL.md) — hard-crash skip-list and localization patterns for crash-prone services or attributes
- [`change-detection`](../change-detection/SKILL.md) — detecting what changed instead of re-reading the whole project

## Exception Handling

- `GetAttributes()` / `SetAttributes()` throw if any requested attribute name does not exist on the object — validate with `GetAttributeInfos()` first when attribute names are dynamic.
- Exceeding practical reference limits (approaching 500,000 live proxies) can cause severe slowdowns or memory pressure; prefer releasing/re-fetching via `ObjectIdentifierProvider` over holding every object for the app's lifetime.
