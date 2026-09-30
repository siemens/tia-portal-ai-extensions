---
name: object-tree-walking
description: Walking TIA Portal Openness object trees schema-free using GetServiceInfos/GetService/GetAttributeInfos/GetAttribute, matching objects by Name+TypeIdentifier, traversing composition properties via reflection, preventing cycles, and deduplicating COM proxy visits. Use when writing code that compares, inspects, or mirrors two Openness object trees dynamically without prior knowledge of the schema.
metadata:
  siemens-depends-on: "openness-base, engineering-objects, devices-and-hardware"
---

# Object Tree Walking (Schema-Free)

## Overview

Walking an Openness object tree dynamically — reading all attributes, discovering services, and recursing into sub-objects without hard-coding the schema — requires several non-obvious patterns. The standard `GetServiceInfos` + `GetService` + `GetAttributeInfos` + `GetAttribute` sequence differs from simple `GetService<T>()` usage in important ways that affect correctness, crash safety, and cycle prevention.

---

## When to Use

- Comparing two Openness object trees in parallel (e.g. reference vs. candidate project).
- Building a generic inspector or exporter that must work on any device family.
- Walking objects where the set of services and attributes varies by device model at runtime.
- Diagnosing: `NullReferenceException` on `GetServiceInfos()` via reflection, infinite recursion through back-reference properties, duplicate nodes when the same COM object is visited via multiple proxy instances.

---

## 1. `GetServiceInfos()` Is an Explicit Interface Implementation — Cast Before Calling

`GetServiceInfos()` is **not** accessible on the concrete proxy type. Calling it via reflection or directly on the object variable returns `null` or throws `MissingMethodException`. Always cast to `IEngineeringServiceProvider` first.

```csharp
// Correct
if (obj is IEngineeringServiceProvider provider)
{
	IList<EngineeringServiceInfo> infos = provider.GetServiceInfos();
	foreach (EngineeringServiceInfo info in infos)
	{
		// Use the non-generic IServiceProvider.GetService(Type) to call dynamically
		object? svc = ((System.IServiceProvider)provider).GetService(info.Type);
	}
}

// Wrong — returns null; method is an explicit interface impl, invisible on the proxy type
obj.GetType().GetMethod("GetServiceInfos")?.Invoke(obj, null); // null
```

The service list is **runtime-dynamic**: it differs per device family, firmware version, and installed extensions. Never hardcode an expected list.

---

## 2. Call `GetServiceInfos()` Before `GetService()` During Full Traversal

`GetServiceInfos()` may register internal descriptors server-side that `GetService<T>()` requires. Calling `GetService<T>()` alone, without a preceding `GetServiceInfos()` on the same object, can silently return `null` and makes a traversal an invalid repro for crashes that only manifest in the full sequence (see [`crash-diagnosis`](../crash-diagnosis/SKILL.md)).

```csharp
// Correct order
var infos = provider.GetServiceInfos();          // primes server-side state
foreach (var info in infos)
{
	var svc = ((System.IServiceProvider)provider).GetService(info.Type);
	if (svc is IEngineeringObject svcObj)
		WalkObject(svcObj);
}
```

---

## 3. Match Objects by `Name::TypeIdentifier` Key, Not by Name Alone

Two objects with the same `Name` but different `TypeIdentifier` are different elements. Combining both gives a stable, unambiguous match key:

```csharp
private static string BuildMatchKey(IEngineeringObject obj)
{
	string name   = TryGetAttribute(obj, "Name")           ?? string.Empty;
	string typeId = TryGetAttribute(obj, "TypeIdentifier") ?? string.Empty;
	return string.IsNullOrEmpty(typeId) ? name : name + "::" + typeId;
}

private static string? TryGetAttribute(IEngineeringObject obj, string attrName)
{
	try   { return obj.GetAttribute(attrName)?.ToString(); }
	catch { return null; }
}
```

**Positional fallback for unnamed objects:** some objects (e.g. `HwIdentifier`, `Address`) have no `Name` and no `TypeIdentifier`. All produce an empty key and would collide. Use a positional index suffix (`"#pos:0"`, `"#pos:1"`) so each gets its own slot and is matched by position within its parent:

```csharp
if (string.IsNullOrEmpty(key))
	key = "#pos:" + index;
```

---

## 4. Use `IEngineeringObject.Equals()` for Identity — Not `==`

The same underlying COM object can be wrapped in multiple distinct .NET proxy instances during traversal. `==` compares .NET reference identity of the wrapper, not the underlying object. `IEngineeringObject` overrides `Equals()` to compare underlying COM identity.

```csharp
// Correct — use Equals()-based comparison; HashSet<IEngineeringObject> works correctly
var visited = new HashSet<IEngineeringObject>(); // Equals is overridden for COM identity

// Wrong — ref equality on proxies; the same COM object via two different proxies is !=
if (visited.Contains(obj)) ...  // only safe because HashSet uses Equals() internally
```

When you need a **pair** key (e.g. reference-object + candidate-object), define a struct that delegates to `Equals()` on both members:

```csharp
private readonly struct ObjectPairKey : IEquatable<ObjectPairKey>
{
	private readonly IEngineeringObject _ref;
	private readonly IEngineeringObject _cand;
	public ObjectPairKey(IEngineeringObject r, IEngineeringObject c) { _ref = r; _cand = c; }
	public bool Equals(ObjectPairKey o) => _ref.Equals(o._ref) && _cand.Equals(o._cand);
	public override bool Equals(object? obj) => obj is ObjectPairKey k && Equals(k);
	public override int GetHashCode() { unchecked { return (_ref.GetHashCode() * 397) ^ _cand.GetHashCode(); } }
}
```

---

## 5. Prevent Infinite Cycles — Per-Path `HashSet<Type>` Service Blacklist

Service traversal can form cycles: `NetworkPort` has a service `NetworkInterface`; `NetworkInterface` has a composition `Ports`; each port has service `NetworkInterface` again. Carry a `HashSet<Type>` of already-entered service types **down the recursion stack** and skip any type already in it.

```csharp
private void WalkServices(IEngineeringObject obj, HashSet<Type> visitedTypes)
{
	if (obj is not IEngineeringServiceProvider provider) return;
	foreach (EngineeringServiceInfo info in provider.GetServiceInfos())
	{
		if (visitedTypes.Contains(info.Type)) continue; // cycle guard

		// Copy the set for the child call — do NOT mutate the parent's set
		var childVisited = new HashSet<Type>(visitedTypes) { info.Type };

		var svc = ((System.IServiceProvider)provider).GetService(info.Type) as IEngineeringObject;
		if (svc != null)
			WalkServices(svc, childVisited);
	}
}
```

The set is **per-path** (copied for each child), not global — the same service type can appear in parallel branches of the tree.

---

## 6. Walk Composition Properties via Reflection; Emit a Grouping Node per Property

Enumerable `IEngineeringObject` properties (e.g. `RegisteredAddresses`, `RegisteredHwIdentifiers`, `RuntimeGroups`) are not reachable via `GetServiceInfos()`. Discover them via `Type.GetProperties()` on the concrete proxy type, filter to `IEnumerable<IEngineeringObject>`, and recurse into each item.

**Critical:** wrap the collection's children in a **grouping node** whose display name equals the property name. Without this, the property name only exists in the slash-delimited path string and is invisible in any tree UI or report.

```csharp
foreach (PropertyInfo prop in obj.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
{
	if (skipNames.Contains(prop.Name)) continue;
	Type? elementType = GetEnumerableElementType(prop.PropertyType);
	if (elementType == null || !typeof(IEngineeringObject).IsAssignableFrom(elementType)) continue;

	if (visitedTypes.Contains(elementType)) continue; // cycle guard for self-referential compositions

	var items = EnumerateSafe(obj, prop.Name);
	if (items.Count == 0) continue;

	var childVisited = new HashSet<Type>(visitedTypes) { elementType };
	// Emit a grouping node — property name becomes the visible label
	ProcessGroup(prop.Name, items, childVisited);
}
```

---

## 7. Skip Back-Reference Properties to Prevent Upward Cycles

Several Openness properties are navigation back-references that lead back up the tree:

| Property | On Type | Points to |
|---|---|---|
| `Parent` | any | parent object |
| `OwnedBy` | any | owning container |
| `Interface` | `NetworkPort` | owning `NetworkInterface` |
| `ConnectedSubnet` | `Node` | project-level `Subnet` |
| `AddressControllers` | `Address` | back to PLC |
| `HwIdentifierControllers` | `HwIdentifier` | back to PLC |
| `Software` | `SoftwareContainer` | enters the full `PlcSoftware` tree |

Maintain a `HashSet<string>` of skip names and check it before walking any property.

---

## 8. Display Name Resolution for Service Nodes

Service objects in Openness often inherit the parent device item's `Name` attribute — they have no distinct name of their own. Resolution order:

1. `nameOverride` — passed explicitly by the caller (e.g. the C# service type name `"AddressController"`).
2. `GetAttribute("Name")` on the object — used when the object has a genuine own name.
3. `obj.GetType().Name` — C# type name as a final fallback.

```csharp
string name = nameOverride
		   ?? TryGetAttribute(obj, "Name")
		   ?? obj.GetType().Name;
```

When entering a service, pass `nameOverride: serviceType.Name` so the node label reflects the service type rather than echoing the parent's name.

---

## 9. Skip Own-Attribute Comparison for Services That Mirror Parent Attributes

Some service types (e.g. `SoftwareContainer`, `PlcUnitProvider`) expose the same attributes as their parent `DeviceItem`. Comparing both the `DeviceItem` attributes and the service's attributes reports every difference twice.

Pass a `skipOwnAttributes` flag when entering these service types:

```csharp
private static readonly HashSet<string> _skipOwnAttributesTypeNames = new()
{
	"Siemens.Engineering.HW.Features.SoftwareContainer",
	"Siemens.Engineering.SW.Units.PlcUnitProvider",
};

bool skipAttrs = _skipOwnAttributesTypeNames.Contains(serviceType.FullName ?? string.Empty);
// pass skipAttrs into the recursive walk call
```

---

## 10. Deduplicate Mirrored Attribute Diffs Across Nested Module Items

PROFINET/GSDML modules sometimes mirror the same attribute (e.g. `SharedDeviceAccessType`) across the outer `DeviceItem` and each of its nested inner `DeviceItem`s. Deduplicate by keying on `"{rootDevice}|{attrName}|{refVal}|{candVal}"`:

```csharp
string rootDevice = parentPath.Contains('/')
	? parentPath.Substring(0, parentPath.IndexOf('/'))
	: parentPath;
string dedupKey = rootDevice + "|" + attrName + "|" + refVal + "|" + candVal;
if (_reportedDiffAttributes.Add(dedupKey))
	emitDiff(...);
// else: already emitted for this device — skip
```

---

## Anti-Patterns

| Anti-pattern | Why it fails | Correct alternative |
|---|---|---|
| `obj.GetType().GetMethod("GetServiceInfos").Invoke(obj, null)` | Explicit interface impl; reflection on concrete type returns null | Cast: `((IEngineeringServiceProvider)obj).GetServiceInfos()` |
| `GetService<T>()` without preceding `GetServiceInfos()` | Skips server-side state priming; service may return null; traversal is an invalid crash repro | Always call `GetServiceInfos()` first on the same object |
| `if (obj == other)` for dedup | `==` compares .NET proxy references; two proxies for the same COM object are `!=` | `if (obj.Equals(other))` — Openness overrides `Equals` for COM identity |
| Emitting collection children without a grouping node | Property name only appears in the path string; invisible as a tree node | Wrap children in a grouping node with display name = property name |
| Walking `Parent`, `Interface`, `ConnectedSubnet` as generic properties | Back-references; traversal immediately re-enters the parent subtree and recurses infinitely | Maintain `_skipPropertyNames` set and check before walking any property |
| Global `HashSet<Type>` visited set shared across all branches | Prevents the same service type from appearing in sibling branches | Copy the set for each child call: `new HashSet<Type>(visited) { newType }` |

---

## Quick Reference

| Goal | API / Pattern |
|---|---|
| Discover available services | `((IEngineeringServiceProvider)obj).GetServiceInfos()` |
| Get service dynamically | `((System.IServiceProvider)provider).GetService(info.Type)` |
| Enumerate all attributes | `obj.GetAttributeInfos()` → filter by `AccessMode` → `obj.GetAttribute(info.Name)` |
| Match objects across two collections | Key = `Name + "::" + TypeIdentifier`; `"#pos:N"` for nameless items |
| Proxy identity equality | `obj.Equals(other)` — not `==`; safe in `HashSet<IEngineeringObject>` |
| Cycle prevention | Per-path `HashSet<Type>` copied into each child call |
| Display name for service nodes | `nameOverride ?? GetAttribute("Name") ?? obj.GetType().Name` |
| Grouping node for composition property | Display name = property name; children = matched items |

## Related Files

- [`engineering-objects`](../engineering-objects/SKILL.md) — `GetService<T>`, `GetAttributeInfos`, attribute read/write
- [`crash-diagnosis`](../crash-diagnosis/SKILL.md) — why `GetServiceInfos()` ordering matters for crash isolation
- [`devices-and-hardware`](../devices-and-hardware/SKILL.md) — device/DeviceItem tree structure
