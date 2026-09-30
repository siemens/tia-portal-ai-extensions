---
name: session-and-project
description: Session and project management for TIA Portal Openness. Use when working with TiaPortal instances, opening/closing projects, attaching to processes, archiving, and managing the project lifecycle.
metadata:
  siemens-depends-on: "openness-base"
---

# Session and Project Management

## Overview

This skill covers patterns for managing TIA Portal sessions and projects using the Siemens Engineering SDK. It includes starting new instances, attaching to running processes, opening/closing projects, and archiving/retrieving project files.

These operations form the foundation of any TIA Portal Openness automation — you must establish a session and load a project before performing any engineering tasks.

## Required Namespaces

```csharp
using Siemens.Engineering;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`

---

## 🛑 MANDATORY CHECK BEFORE CODING: TIA Portal Version Requirement

**BEFORE you write ANY code that uses the Siemens Engineering SDK, you MUST ask the user for their TIA Portal version.**

This is a **blocking requirement** — do NOT proceed to generate code without a confirmed, valid TIA Portal version.

### Minimum Supported Version

These skills only support **TIA Portal V21 and higher**. Any version below V21 is **NOT supported**.

### How to Ask

Use the `ask_user` tool with a clear message and a freeform text input for the version number. Example:

```
I need to know your TIA Portal version to set up the SDK references correctly.

What TIA Portal version are you using?
```

Use the `ask_user` tool as follows:

```
question: "What TIA Portal version are you using? (minimum V21)"
allow_freeform: true
```

### Validation Rules

After receiving the user's response, you MUST validate:

| Condition | Action |
|---|---|
| Version **>= 21** | Accept and use it in the code |
| Version **< 21** | **REJECT** — inform the user that TIA Portal V21 or higher is required, then re-ask |
| Non-numeric response | **REJECT** — clarify that a numeric version is expected, then re-ask |
| No response / unclear | **REJECT** — re-ask politely |

### Example of Rejection & Re-asking

If the user says "18" or "19":

```
I'm sorry, but these skills only support TIA Portal V21 and higher. V18 is not compatible with this automation framework.

Please provide a TIA Portal version of 21 or higher, or upgrade your TIA Portal installation.
```

### What You Must NOT Do

- ❌ Do NOT assume a default version without asking
- ❌ Do NOT use V18 or V19 as default in generated code
- ❌ Do NOT skip asking just because the user did not mention a version
- ❌ Do NOT start generating code before you have a valid TIA Portal version (>= 21)

---

### Find SDK DLLs via Registry

**Description:** The Siemens Engineering SDK DLLs are not in the GAC and their locations depend on the installed TIA Portal version. Use the Windows registry to discover the installation path dynamically.

**SDK-Style .csproj Example:**
Always use the SDK-style project format with `net48` target framework.

```xml
<!-- IMPORTANT: Minimum supported version is V21 -->
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TiaVersion>21</TiaVersion>
    <TiaPortalLocation>$([MSBuild]::GetRegistryValueFromView(`HKEY_LOCAL_MACHINE\SOFTWARE\Siemens\Automation\_InstalledSW\TIAP$(TiaVersion)\Global`, `Path`, '', RegistryView.Registry64, RegistryView.Registry32))</TiaPortalLocation>
  </PropertyGroup>

  <PropertyGroup>
    <TargetFramework>net48</TargetFramework>
    <LangVersion>latest</LangVersion>
    <ImplicitUsings>enable</ImplicitUsings>
    <OutputType>Exe</OutputType>
  </PropertyGroup>

  <ItemGroup>
    <Reference Include="Siemens.Engineering.Base">
      <HintPath>$(TiaPortalLocation)\PublicAPI\V$(TiaVersion)\net48\Siemens.Engineering.Base.dll</HintPath>
      <Private>False</Private>
      <SpecificVersion>False</SpecificVersion>
    </Reference>
  </ItemGroup>
</Project>
```

**Key Details:**
- The registry key path is `HKEY_LOCAL_MACHINE\SOFTWARE\Siemens\Automation\_InstalledSW\TIAP$(TiaVersion)\Global`
- The `Path` value under this key contains the TIA Portal installation directory
- DLLs are located under `\PublicAPI\V$(TiaVersion)\net48\`
- Use `RegistryView.Registry64` first, falling back to `RegistryView.Registry32` for compatibility
- **Minimum version is V21** — always set `<TiaVersion>21</TiaVersion>` as the minimum default

### Assembly Resolver — `[MethodImpl(NoInlining)]` Requirement

Any method that registers `AppDomain.CurrentDomain.AssemblyResolve` **must not** also contain references to `Siemens.Engineering` types in the same method body. If they are in the same method, the JIT may compile the `Siemens.Engineering` references before the resolve handler is registered, causing an `AssemblyLoadException` on startup.

**Pattern:** split into two methods and annotate the entry point `[MethodImpl(MethodImplOptions.NoInlining)]` to prevent the JIT from merging them:

```csharp
// Entry point — registers the resolver BEFORE any Openness types are referenced
[MethodImpl(MethodImplOptions.NoInlining)]
public static void Initialize()
{
    AppDomain.CurrentDomain.AssemblyResolve += ResolveOpenness;
    InitializeCore();   // Openness types are only referenced inside here
}

// Separated method — JIT compiles this only AFTER the resolver is already registered
[MethodImpl(MethodImplOptions.NoInlining)]
private static void InitializeCore()
{
    var tia = new TiaPortal(TiaPortalMode.WithoutUserInterface);
    // ... use Openness types freely ...
}
```

Never merge the `AssemblyResolve` registration and Openness API calls into a single method.

## Common Patterns

### Start New TIA Portal Instance (with UI)

**Description:** Launches a new TIA Portal process with a visible user interface. Use this mode when you want the user to see and interact with TIA Portal during automation.

**Example:**
```csharp
var tia = new Siemens.Engineering.TiaPortal(TiaPortalMode.WithUserInterface);
```

**Key Types and Methods:**
- `TiaPortal` — the main entry point for all Openness operations
- `TiaPortalMode.WithUserInterface` — enum value that shows the TIA Portal UI

---

### Discover Running TIA Portal Processes

**Description:** Retrieves a list of all running TIA Portal processes on the machine. Useful when you want to attach to an already-open instance instead of starting a new one.

**Example:**
```csharp
var tiaProcesses = Siemens.Engineering.TiaPortal.GetProcesses();
```

**Key Types and Methods:**
- `TiaPortal.GetProcesses()` — returns a collection of `TiaPortalProcess` objects
- `TiaPortalProcess` — represents a running TIA Portal process

---

### Attach to Existing TIA Portal Process

**Description:** Connects to an already-running TIA Portal process. This avoids starting a duplicate instance and lets your automation work alongside the user's active session.

**Example:**
```csharp
foreach (var tiaPortalProcess in tiaProcesses)
{
    TiaPortalInstance = tiaPortalProcess.Attach();
}
```

**Key Types and Methods:**
- `TiaPortalProcess.Attach()` — attaches to the process and returns a `TiaPortal` instance
- `TiaPortal` — the session object used for all subsequent operations

---

### Get & Dispose Current Process

**Description:** Retrieves the TIA Portal process that owns the current automation context and disposes of it when no longer needed. Important for cleanup and avoiding orphaned processes.

**Example:**
```csharp
tia.GetCurrentProcess().Dispose();
```

**Key Types and Methods:**
- `TiaPortal.GetCurrentProcess()` — returns the process associated with the session
- `Process.Dispose()` — releases resources held by the process

🛑 **Do NOT call `Dispose()` on `TiaPortalProcess` handles obtained from `TiaPortal.GetProcesses()` in TIA Portal V21.** Confirmed root cause: `Dispose()` on a process handle from `GetProcesses()` **tears down the live TIA Portal instance**, not just the local proxy/handle. This is easy to trigger accidentally — e.g. a "refresh the process list" action that calls `Dispose()` on each previously-enumerated handle before re-listing will silently crash the user's running TIA Portal session. `GetCurrentProcess().Dispose()` (your own session's process, shown above) is a different, safe case — the danger is specifically iterating `GetProcesses()` results (e.g. to build an attach-target list) and disposing them.

```csharp
// WRONG — kills the live TIA Portal instance in V21
foreach (var p in Siemens.Engineering.TiaPortal.GetProcesses())
{
    // ... use p for display/attach ...
    p.Dispose();   // <-- do not do this
}

// CORRECT — just don't dispose handles from GetProcesses(); let them be garbage collected
foreach (var p in Siemens.Engineering.TiaPortal.GetProcesses())
{
    // ... use p for display/attach only ...
}
```

---

### Iterate Open Projects

**Description:** Enumerates all projects currently loaded in the TIA Portal session. Use this pattern to discover available projects without knowing their file paths.

**Example:**
```csharp
foreach (var project in TiaPortalInstance.Projects)
{
    // Access each project
}
```

**Key Types and Methods:**
- `TiaPortal.Projects` — a `ProjectCollection` (implements `IEngineeringComposition<IProject>`)

---

### Open Project from File (.ap19)

**Description:** Opens an existing TIA Portal project from its `.ap19` file on disk.

**Example:**
```csharp
FileInfo fileInfo = new("C:/MyPathToTheTiaProject.ap19");
tia.Projects.Open(fileInfo);
```

**Key Types and Methods:**
- `ProjectCollection.Open(FileInfo)` — opens the project file and returns a `Project`
- `Project` — represents an open TIA Portal project

---

### Retrieve Project from Archive (.zap)

**Description:** Extracts a TIA Portal project from a `.zap` archive file. The archive is unpacked to a temporary directory before being loaded.

**Example:**
```csharp
FileInfo sourcePath = new(myStep7ProjectArchivePath);
DirectoryInfo targetDir = new DirectoryInfo(Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString()));
Project = TiaPortalInstance.Projects.Retrieve(sourcePath, targetDir);
```

**Key Types and Methods:**
- `ProjectCollection.Retrieve(FileInfo, DirectoryInfo)` — extracts and loads the archived project
- `Project` — the loaded project instance

---

### Save Project

**Description:** Saves all changes to the current project on disk.

**Example:**
```csharp
project.Save();
```

**Key Types and Methods:**
- `Project.Save()` — persists project changes to disk

---

### Archive (Export) Project to .zap

**Description:** Exports the project to a compressed `.zap` archive file. Useful for backup or distribution.

**Example:**
```csharp
project.Archive(new DirectoryInfo(Path.GetTempPath()), "dummy.zap21",
    ProjectArchivationMode.Compressed);
```

**Key Types and Methods:**
- `Project.Archive(DirectoryInfo, string, ProjectArchivationMode)` — creates the archive
- `ProjectArchivationMode.Compressed` — produces a smaller archive file

---

### Close Project

**Description:** Closes the project, releasing it from the TIA Portal session.

**Example:**
```csharp
project.Close();
```

**Key Types and Methods:**
- `Project.Close()` — unloads the project from the session

---

### Gate teardown by project and portal-instance ownership independently

Do **not** unconditionally call `Project.Close()` or `TiaPortal.Dispose()` from shared teardown code. Track ownership of the project and the portal instance separately: an application can attach to an existing, empty portal instance and then open a project itself. A single ownership flag conflates those independent lifecycles.

```csharp
public Task CloseAsync()
{
    if (_ownsProject)
    {
        _project?.Close();
    }

    if (_ownsTiaPortalInstance)
    {
        _tiaPortal?.Dispose();
    }
    return Task.CompletedTask;
}
```

**Key points:**
- Close the project only when `_ownsProject`; dispose the portal only when `_ownsTiaPortalInstance`.
- An attached portal can be user-owned while a project opened by this application is application-owned; close only the latter during teardown.
- `PlugNew`, `CreateWithItem`, and other mutations stay **in memory** until `Project.Save()` is called. Save explicitly before teardown when this application owns and intends to persist its changes; shared teardown must not save automatically.

---

### One Project Per TiaPortal Instance

**Description:** A single `TiaPortal` instance can hold only **one** open project at a time. This is a hard runtime limit — it is NOT lifted by `TiaPortalMode.WithUserInterface`. Attempting to open a second project into the same portal instance throws `EngineeringTargetInvocationException` with the message "Another project is already open".

To work with two projects simultaneously (e.g. for cross-project comparison or copying), create two separate `TiaPortal` instances:

**Example:**
```csharp
// WRONG — throws if a project is already open in tia
tia.Projects.Open(secondProjectFile);

// CORRECT — use a second TiaPortal instance for the second project
using var tia1 = new TiaPortal(TiaPortalMode.WithoutUserInterface);
using var tia2 = new TiaPortal(TiaPortalMode.WithoutUserInterface);
var project1 = tia1.Projects.Open(firstProjectFile);
var project2 = tia2.Projects.Open(secondProjectFile);
```

**Key Types and Methods:**
- `TiaPortal` — each instance is an independent portal process; one project per instance
- `EngineeringTargetInvocationException` — thrown when opening a second project into an already-occupied portal instance

---

### TIA Portal Reference (Secondary) Project

**Description:** Openness has no equivalent of the TIA Portal GUI's "Reference project" feature. Instead, it offers its own **read-only, hidden secondary project** that can be opened alongside the primary project. Use it to copy data into the primary project or to compare the two — the primary project remains the only one the interactive user sees and edits.

**Key points:**
- The secondary project is read-only from Openness — do not attempt to modify it directly; copy objects from it into the primary project instead.
- Because a `TiaPortal` instance holds only **one** project open for *editing* (see above), the secondary/reference project is a distinct mechanism, not a second primary project.

### Multiuser Support via ProjectBase

**Description:** Since TIA Portal V17, single-user and multiuser projects share a common base class, `ProjectBase`. Write code against `ProjectBase` instead of the concrete `Project` (single-user) or `MultiuserProject` (multiuser, via TIA Project-Server) type, and the same code supports both project kinds without branching.

**Example:**
```csharp
// Works for both single-user (Project) and multiuser (MultiuserProject) projects
void ProcessProject(ProjectBase project)
{
    Console.WriteLine(project.Name);
}
```

**Key Types and Methods:**
- `ProjectBase` — common base class for `Project` and `MultiuserProject`
- `ProjectBase.CreationTime` / `ProjectBase.LastModified` — project-level change detection (see [`change-detection`](../change-detection/SKILL.md))

## Quick Reference

| Method / Pattern | Purpose |
|---|---|
| `new TiaPortal(TiaPortalMode.WithUserInterface)` | Start a new TIA Portal instance with UI |
| `TiaPortal.GetProcesses()` | Discover running TIA Portal processes |
| `TiaPortalProcess.Attach()` | Attach to an existing TIA Portal process |
| `TiaPortal.GetCurrentProcess().Dispose()` | Get and dispose the current process (safe — your own session's process) |
| Never `Dispose()` handles from `GetProcesses()` | Disposing a process handle obtained via `GetProcesses()` kills the live TIA Portal instance in V21 |
| `TiaPortal.Projects` (iterate) | Enumerate open projects |
| `ProjectCollection.Open(FileInfo)` | Open a project from `.ap19` file |
| `ProjectCollection.Retrieve(FileInfo, DirectoryInfo)` | Extract project from `.zap` archive |
| `Project.Save()` | Save project changes to disk |
| `Project.Archive(...)` | Export project to `.zap` archive |
| `Project.Close()` | Close and unload the project |
| Two `TiaPortal` instances | Required to have two projects open simultaneously |
| `[MethodImpl(NoInlining)]` split pattern | Register `AssemblyResolve` and use Openness types in separate methods to prevent JIT premature compilation |
| Secondary/reference project | Read-only hidden project for copying data into or comparing against the primary project |
| `ProjectBase` | Common base type for `Project`/`MultiuserProject` — write code once for single- and multiuser projects |

## Related Files

- [`engineering-objects`](../engineering-objects/SKILL.md) — patterns for working with engineering objects within a project
- [`crash-diagnosis`](../crash-diagnosis/SKILL.md) — diagnosing hard TIA Portal crashes; breadcrumb patterns; assembly resolver and IPC context
- [`change-detection`](../change-detection/SKILL.md) — `ProjectBase.CreationTime`/`LastModified` for project-level change detection
- [`threading-and-concurrency`](../threading-and-concurrency/SKILL.md) — thread affinity of the `TiaPortal` instance created/attached here

## Exception Handling

- **Process Attach Failures:** If no TIA Portal processes are found, `GetProcesses()` returns an empty collection. Verify the collection before attempting to attach.
- **File Not Found:** Opening or retrieving a project with an invalid path will throw an `ArgumentException` or `IOException`. Validate file existence before calling `Open()` or `Retrieve()`.
- **Project Already Open:** A single `TiaPortal` instance can only hold one project. Opening a second project throws `EngineeringTargetInvocationException` ("Another project is already open"). Use a second `TiaPortal` instance for simultaneous project access.
- **Archive Corruption:** A corrupted `.zap` archive will throw during `Retrieve()`. Wrap archive operations in try/catch blocks.
- **Killing the live instance:** Calling `Dispose()` on a `TiaPortalProcess` obtained from `GetProcesses()` (as opposed to your own `GetCurrentProcess()`) tears down the live TIA Portal instance in V21 — see the warning above. This is a common trap in "refresh process list"/attach-picker UI code.
