---
name: blocks
description: TIA Portal PLC blocks management. Use when importing, compiling, exporting, protecting blocks with passwords, accessing InstanceDB/GlobalDB interface members, and finding cross-references.
metadata:
  siemens-depends-on: "openness-base, engineering-objects"
---

# Blocks

## Overview

Blocks are the fundamental executable and data objects in a TIA Portal PLC project. They include OBs (Organization Blocks), FCs (Function Calls), FBs (Function Blocks), DBs (Data Blocks), and SFCs. The `PlcSoftware.BlockGroup` provides access to all blocks. Blocks can be imported, compiled, exported, password-protected, and analyzed for cross-references. InstanceDB and GlobalDB blocks expose interface members that define their variable declarations.

## Required Namespaces

```csharp
using Siemens.Engineering;
using Siemens.Engineering.Compiler;
using Siemens.Engineering.CrossReference;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Blocks;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`

## Common Patterns

### Access Block Composition from PlcSoftware

**Description:** Retrieve the block composition from `PlcSoftware` to enumerate or search for blocks. The `BlockGroup.Blocks` collection contains all PLC blocks at that group level.

**Example:**

```csharp
var blockComposition = plcSoftware.BlockGroup.Blocks;
```

**Key Types and Methods:**
- `PlcSoftware.BlockGroup` — root container for all blocks
- `PlcBlockComposition` — collection of PLC blocks (one group level only)

### Find Block Recursively

**Description:** `Blocks.Find(name)` searches only the current group level. To find a block anywhere in the hierarchy, recurse into sub-groups. For a PLC-wide search that also covers SW-Unit groups, see [`sw-units`](../sw-units/SKILL.md).

**Example:**

```csharp
PlcBlock FindBlockRecursive(PlcBlockGroup group, string name)
{
    var result = group.Blocks.Find(name);
    if (result != null) return result;
    foreach (var sub in group.Groups)
    {
        result = FindBlockRecursive(sub, name);
        if (result != null) return result;
    }
    return null;
}
```

**Key Types and Methods:**
- `PlcBlockGroup.Blocks.Find(name)` — single-level lookup; returns `null` if not found at this level
- `PlcBlockGroup.Groups` — sub-folder composition; iterate to recurse

### Import Blocks into Composition

**Description:** Import block files into the block composition. Three distinct import paths exist — using the wrong API for a given format will fail silently or throw.

| Source type | API | Notes |
|---|---|---|
| XML block export (`.xml`) | `PlcBlockComposition.Import(FileInfo, ImportOptions)` | Direct import |
| SCL text source (`.scl`) | `ExternalSourceGroup` → `CreateFromFile` → `GenerateBlocksFromSource` | Two-step: register + compile |
| SIMATIC SD document (`.s7dcl`, V21) | `PlcBlockComposition.ImportFromDocuments(dir, name, options)` | Direct document import — see [`simatic-sd`](../simatic-sd/SKILL.md) |

**XML import example:**

```csharp
targetBlockGroup.Blocks.Import(new FileInfo(xmlFilePath), ImportOptions.Override);
```

**SCL import via ExternalSources example:**

```csharp
// Use the target SW-Unit's ExternalSourceGroup when placing inside a SW-Unit
var externalSource = externalSourceGroup.ExternalSources.CreateFromFile(
    sourceFile.Name, sourceFile.FullName);
externalSource.GenerateBlocksFromSource();
externalSource.Delete();
```

**Key Types and Methods:**
- `PlcBlockComposition.Import(FileInfo, ImportOptions)` — XML only; do NOT use for `.scl` or `.s7dcl`
- `ExternalSourceGroup.ExternalSources.CreateFromFile` — registers an SCL/text source
- `PlcExternalSource.GenerateBlocksFromSource()` — compiles the registered source into blocks
- `PlcBlockComposition.ImportFromDocuments(DirectoryInfo, string, ImportDocumentOptions)` — SD documents (V21)

**Import anti-patterns:**
- Do NOT call `Import` on an `.scl` file — that API is XML-only.
- Do NOT use `ExternalSources.CreateFromFile` + `GenerateBlocksFromSource` on `.s7dcl` — use `ImportFromDocuments`.

### Import Order Rule

When importing multiple block types in one operation, always follow this order to avoid unresolved-type errors:

1. **PLC Data Types (UDTs)** — must exist before any block that references them in its interface
2. **FBs and FCs** — may reference UDTs
3. **OBs and Instance DBs** — may reference FBs/FCs

Violating this order causes `EngineeringException` ("Unresolved type reference") at import or compile time.

### Compile and Export Block

**Description:** Obtain the `ICompilable` service from a block or from `PlcSoftware` itself, trigger compilation, check the result, then export the block to a file.

**Example:**

```csharp
var block = plcSoftware.BlockGroup.Blocks.First(b => b.Name == "Axis_blue");

// Compile a single block
var compiler = block.GetService<ICompilable>();
var result   = compiler.Compile();
// Inspect result.State and result.Messages — do not assume success
if (result.State == CompilationResultState.Success)
    block.Export(fileInfo, ExportOptions.None);

// Compile the entire PlcSoftware
var swCompiler = plcSoftware.GetService<ICompilable>();
var swResult   = swCompiler.Compile();
```

**Key Types and Methods:**
- `ICompilable` — service available on individual blocks and on `PlcSoftware`
- `ICompilable.Compile()` — compiles and returns a result object
- `CompilationResult.State` — overall outcome (`Success`, `Warning`, `Error`)
- `CompilationResult.Messages` — individual compiler messages with severity
- `PlcBlock.Export(FileInfo, ExportOptions)` — exports the block as XML

### Compile Scopes — Choose the Right Object to Compile

**Description:** `ICompilable` is available on several object types, each compiling a different scope. Requesting the service from the wrong level either compiles too much (wasting time) or too little (missing hardware/software consistency checks).

| Scope | Call `ICompilable` on | Notes |
|---|---|---|
| Hardware only | `DeviceItem` | Compiles the hardware configuration only, no PLC program |
| Software only | `PlcSoftware` | Compiles the PLC user program only, no hardware config |
| Hardware + Software | `Device` | Compiles hardware configuration and software together |
| Single block | the `PlcBlock` itself | Compiles just that one program block |

```csharp
// Hardware only
ICompilable hwCompiler = deviceItem.GetService<ICompilable>();
CompilerResult hwResult = hwCompiler.Compile();

// Software only
ICompilable swCompiler = plcSoftware.GetService<ICompilable>();
CompilerResult swResult = swCompiler.Compile();

// Hardware + software together
ICompilable deviceCompiler = device.GetService<ICompilable>();
CompilerResult deviceResult = deviceCompiler.Compile();
```

**Key points:**
- Prefer the narrowest scope that answers your question — e.g. compile a single block during iterative development instead of the whole `PlcSoftware`.
- Use `Device`-level compile when hardware and software consistency must be validated together (e.g. before download).

### Compile Diagnostics — recurse into nested `CompilationResult.Messages`

**Description:** Reading only the top-level `CompilationResult.Messages[].Description` often yields empty or summary-only text. The detailed compiler diagnostics can live on each message's nested `Messages` composition, so treat compile output as a tree rather than a flat list.

**Example:**

```csharp
IEnumerable<string> FlattenMessages(IEnumerable<CompilerResultMessage> messages)
{
    foreach (var message in messages)
    {
        if (!string.IsNullOrWhiteSpace(message.Description))
            yield return message.Description;

        foreach (var nested in FlattenMessages(message.Messages))
            yield return nested;
    }
}

var readableMessages = FlattenMessages(result.Messages).ToList();
```

**Key points:**
- Recurse before concluding that a compile failed "without useful error text" — the useful text is often nested.
- Use `CompilationResult.ErrorCount` or `CompilationResult.State` first to decide whether you need to flatten the message tree.
- Keep both the summary rows and the nested leaf messages when reporting diagnostics to a user.

### Protect Block with Password

**Description:** Apply password protection to a block using the `PlcBlockProtectionProvider` service. Validate password characters before setting to ensure they meet the provider's requirements.

**Example:**

```csharp
var protectionProvider = block.GetService<PlcBlockProtectionProvider>();
var invalidChars = protectionProvider.GetInvalidPasswordCharacters().ToList();
protectionProvider.Protect(securePassword);
```

**Key Types and Methods:**
- `PlcBlockProtectionProvider` — service for managing block protection
- `GetInvalidPasswordCharacters()` — returns characters that are not allowed in passwords
- `Protect(SecureString)` — applies password protection to the block

### Get InstanceDB and GlobalDB Interface Members

**Description:** Access the interface members (variable declarations) of InstanceDB and GlobalDB blocks. Use pattern matching with `is not` to safely cast the block type before accessing its `Interface.Members`.

**Example:**

```csharp
if (plcSoftware.BlockGroup.Blocks.First(x => x.Name == "Axis_red_DB") is not InstanceDB instanceDb) return;
var instanceMembers = instanceDb.Interface.Members;
```

**Key Types and Methods:**
- `InstanceDB` — data block instance associated with an FB
- `InstanceDB.Interface.Members` — collection of variable declarations
- `GlobalDB` — standalone global data block
- `GlobalDB.Interface.Members` — collection of variable declarations

### Get Cross References for a Block

**Description:** Analyze which other blocks reference a given block using the `CrossReferenceService`. Filter by `AllObjects` or other criteria to get a comprehensive view of block dependencies.

**Example:**

```csharp
var db = plcSoftware.BlockGroup.Blocks.First(x => x.Name == "Axis_red_DB");
var crossRefService = db.GetService<CrossReferenceService>();
var crossRefs = crossRefService.GetCrossReferences(CrossReferenceFilter.AllObjects).Sources.ToList();
```

**Key Types and Methods:**
- `CrossReferenceService` — service for querying cross-references
- `CrossReferenceFilter.AllObjects` — filter to include all object types
- `CrossReference.Sources` — collection of referencing objects

## Quick Reference

| Method/Pattern | Purpose |
|---|---|
| `software.BlockGroup.Blocks` | Access blocks at the current group level |
| `FindBlockRecursive(group, name)` | Find a block anywhere in the group hierarchy |
| `PlcBlockComposition.Import(path, ImportOptions)` | Import blocks from an XML file |
| `ExternalSources.CreateFromFile` + `GenerateBlocksFromSource` | Import SCL text source |
| `PlcBlockComposition.ImportFromDocuments(dir, name, options)` | Import SIMATIC SD document (V21) |
| `ICompilable.Compile()` | Compile a block or PlcSoftware and get results |
| `ICompilable` on `DeviceItem`/`PlcSoftware`/`Device` | Compile hardware-only / software-only / hardware+software |
| `PlcBlock.Export(path, ExportOptions)` | Export a block as XML |
| `PlcBlockProtectionProvider.Protect(SecureString)` | Password-protect a block |
| `InstanceDB.Interface.Members` | Get variable declarations of an instance DB |
| `GlobalDB.Interface.Members` | Get variable declarations of a global DB |
| `CrossReferenceService.GetCrossReferences()` | Find references to a block |

## Related Files

- [`plc-data-types`](../plc-data-types/SKILL.md) — UDTs live in `TypeGroup`, not `BlockGroup`
- [`sw-units`](../sw-units/SKILL.md) — PLC-wide block search across root and all SW-Unit groups
- [`simatic-sd`](../simatic-sd/SKILL.md) — SD document export/import and network insertion
- [`global-library`](../global-library/SKILL.md) — placing blocks from a GlobalLibrary (MasterCopy or LibraryType)
- [`tags-and-tagtables`](../tags-and-tagtables/SKILL.md) — blocks reference tags defined in tag tables
- [`online-and-download`](../online-and-download/SKILL.md) — blocks are downloaded to the CPU device
- [`libraries-and-alarms`](../libraries-and-alarms/SKILL.md) — libraries may contain reusable blocks
- [`change-detection`](../change-detection/SKILL.md) — `PlcChecksumProvider` and `FingerprintProvider` for detecting program/block changes without recompiling

## Exception Handling

- `EngineeringException` may be thrown during compilation if the block has unresolved references or syntax errors
- `EngineeringException` may occur when importing blocks if the file format is incompatible or corrupted
- Check `CompilationResult.ErrorCount > 0` before attempting to export or download compiled blocks
