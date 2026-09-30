# Add-In Entry Points — Pinned Signatures (TIA Portal V21)

Every signature in this file was **verified by reflection** against
`PublicAPI\V21\net48\Siemens.Engineering.AddIn.Base.dll` of a real V21 installation.

> **Hard rule for the scaffold skill:** never emit an Openness member that is not listed
> in this file. If a required kind or member is missing, verify it by reflection first
> (procedure at the bottom) and extend this file. Do not guess.

All add-in entry-point types live in **`Siemens.Engineering.AddIn.Base.dll`**.

## How TIA Portal finds your code

There is **no `Main`**. TIA Portal reflects over the packaged assembly and instantiates
every public, concrete subclass of one of the `*AddInProvider` base classes below.
Each provider base class is `abstract`, has a `protected` parameterless constructor and
implements `IDisposable` (`protected virtual void Dispose(bool disposing)`).

Consequences for generated code:
- the provider class must be `public` and have a public parameterless constructor
- one provider class per attach point; a single assembly may contain several
- overrides are `protected override` (the `Get…` methods are `protected`, except where
  noted as public below)

---

## 1. Context-menu add-ins

### 1.1 Shared building blocks

Namespace `Siemens.Engineering.AddIn.Menu`:

| Member | Signature |
|---|---|
| `ContextMenuAddIn` | `abstract class`; `protected ContextMenuAddIn(string displayName)` |
| | `protected virtual void BuildContextMenuItems(ContextMenuAddInRoot addInRootSubmenu)` |
| | `public ContextMenuAddInRoot GetSubmenu()` |
| `ContextMenuAddInRoot` | `: MenuItem`; `public ChildItemFactory Items { get; }`, `public string DefaultLabelText { get; }` |
| `Submenu` | `: MenuItem`; `public ChildItemFactory Items { get; }`, `public string DefaultLabelText { get; }` |
| `MenuStatus` | enum: `Enabled`, `Disabled`, `Hidden` |
| `MenuSelectionProvider` | `public IEnumerable<object> GetSelection()` |
| | `public IEnumerable<TRequestedType> GetSelection<TRequestedType>()` |
| `MenuSelectionProvider<T1>` / `<T1,T2>` / `<T1,T2,T3>` | typed variants passed to the delegates |

`ChildItemFactory` (returned by `.Items`):

```csharp
Submenu          AddSubmenu(string text);

ActionItem<T>    AddActionItem<T>(string text, OnClickDelegate onClick);
ActionItem<T>    AddActionItem<T>(string text, OnClickDelegate onClick,
                                  OnUpdateStatusDelegate onUpdateStatus);
ActionItem<T>    AddActionItemWithIcon<T>(string text, System.Drawing.Icon icon,
                                  OnClickDelegate onClick
                                  [, OnUpdateStatusDelegate onUpdateStatus]);
ActionItem<T>    AddActionItemWithCheckBox<T>(string text, OnClickDelegate onClick,
                                  OnUpdateStatusDelegate<CheckBoxActionItemStyle> onUpdateStatus);
ActionItem<T>    AddActionItemWithRadioButton<T>(string text, OnClickDelegate onClick,
                                  OnUpdateStatusDelegate<RadioButtonActionItemStyle> onUpdateStatus);
```

All six also exist with **two** and **three** type arguments
(`AddActionItem<T1,T2>`, `AddActionItem<T1,T2,T3>`, …) returning `ActionItem<T1,T2>` /
`ActionItem<T1,T2,T3>`. The type arguments are the selectable object types the menu item
applies to.

Delegates (nested in `ActionItem<T>`):

```csharp
delegate void       OnClickDelegate(MenuSelectionProvider<T> menuSelectionProvider);
delegate MenuStatus OnUpdateStatusDelegate(MenuSelectionProvider<T> menuSelectionProvider);
delegate TStyle     OnUpdateStatusDelegate<TStyle>(MenuSelectionProvider<T> menuSelectionProvider);
```

> ⚠️ **Changed vs. pre-V21:** `AddActionItem` no longer accepts a trailing error-handler
> delegate. Wrap the click handler in your own `try/catch`.

### 1.2 Providers (attach points)

All four are in namespace `Siemens.Engineering.AddIn` and expose

```csharp
protected override IEnumerable<ContextMenuAddIn> GetContextMenuAddIns()
```

| Attach point in TIA Portal | Base class |
|---|---|
| Project tree | `ProjectTreeAddInProvider` |
| Devices & networks editor | `DevicesAndNetworksAddInProvider` |
| Project library tree | `ProjectLibraryTreeAddInProvider` |
| Global library tree | `GlobalLibraryTreeAddInProvider` |

Minimal shape (identical for all four — only the base class changes):

```csharp
using System.Collections.Generic;
using Siemens.Engineering.AddIn;
using Siemens.Engineering.AddIn.Menu;

public sealed class AddInProvider : ProjectTreeAddInProvider
{
    protected override IEnumerable<ContextMenuAddIn> GetContextMenuAddIns()
    {
        yield return new MyContextMenuAddIn();
    }
}
```

### 1.3 Typical selection types per attach point

The type argument of `AddActionItem<T>` determines on which nodes the entry appears.
These types are **not** in `AddIn.Base` — they come from the Engineering assemblies, so
the matching reference must be added:

| Selection type | Namespace | Assembly |
|---|---|---|
| `Project` | `Siemens.Engineering` | `Siemens.Engineering.Base` |
| `Device` | `Siemens.Engineering.HW` | `Siemens.Engineering.Base` |
| `DeviceItem` | `Siemens.Engineering.HW` | `Siemens.Engineering.Base` |
| `Subnet`, `IoSystem` | `Siemens.Engineering.HW` | `Siemens.Engineering.Base` |
| `PlcSoftware`, `PlcBlock`, `PlcTagTable` | `Siemens.Engineering.SW…` | `Siemens.Engineering.Step7` |
| Library folders / master copies | `Siemens.Engineering.Library…` | `Siemens.Engineering.Base` |

Confirm any type not listed here before using it (see `openness-base`, namespace map).

---

## 2. Version control (VCI) add-ins

Namespace `Siemens.Engineering.AddIn.VersionControl` and its `ImportAddIn` /
`CompositeAddIn` sub-namespaces.

### 2.1 Import add-in

```
VciImportAddInProvider                 (abstract, protected ctor)
  public virtual IEnumerable<VciImportAddIn> GetImportAddIns()

VciImportAddIn                         (abstract, protected VciImportAddIn(string displayName))
  public virtual IEnumerable<ContextMenuAddIn> GetImportContextMenuAddIns()
  public virtual VciImportWorkflowAddIn        GetImportWorkflowAddIn()

VciImportWorkflowAddIn                 (abstract, protected ctor(string displayName))
  public virtual ImportWorkflowSupport GetImportWorkflowSupport()

ImportWorkflowSupport                  (abstract, protected ctor)
  public virtual PreImportWorkflowItem  GetPreImportWorkflowItem()
  public virtual PostImportWorkflowItem GetPostImportWorkflowItem()
  public virtual void InitializeImportSupport()
  public virtual void DisposeImportSupport()

PreImportWorkflowItem                  (abstract, protected ctor)
  public virtual WorkflowExecutionResult Execute(IEnumerable<PreImportInfo> objectsToBeImported,
                                                 ImportContext context)
  public virtual void Rollback(IEnumerable<PreImportInfo> objectsToBeImported,
                               ImportContext context)

PostImportWorkflowItem                 (abstract, protected ctor)
  public virtual WorkflowExecutionResult Execute(IEnumerable<PostImportInfo> objectsToBeImported,
                                                 ImportContext context)
```

### 2.2 Workspace repository / export add-in (composite)

```
VciWorkspaceRepositoryAddInProvider     (abstract, protected ctor)
  public virtual IEnumerable<VciWorkspaceRepositoryAddIn> GetWorkspaceRepositoryAddIns()

VciWorkspaceRepositoryAddIn             (abstract, protected ctor(string displayName))
  public virtual IEnumerable<ContextMenuAddIn>          GetWorkspaceRepositoryContextMenuAddIns()
  public virtual VciWorkspaceRepositoryWorkflowAddIn    GetWorkspaceRepositoryWorkflowAddIn()

VciWorkspaceRepositoryWorkflowAddIn     (abstract, protected ctor(string displayName))
  public virtual ExportWorkflowSupport GetExportWorkflowSupport()

ExportWorkflowSupport                   (abstract, protected ctor)
  public virtual PreExportWorkflowItem  GetPreExportWorkflowItem()
  public virtual PostExportWorkflowItem GetPostExportWorkflowItem()
  public virtual void InitializeExportWorkflowSupport()
  public virtual void DisposeExportWorkflowSupport()

PreExportWorkflowItem                   (abstract, protected ctor)
  public virtual WorkflowExecutionResult Execute(IEnumerable<PreExportInfo> exportableObjects,
                                                 ExportContext context)
  public virtual void Rollback(IEnumerable<PreExportInfo> exportableObjects,
                               ExportContext context)

PostExportWorkflowItem                  (abstract, protected ctor)
  public virtual WorkflowExecutionResult Execute(IEnumerable<PostExportInfo> exportableObjects,
                                                 ExportContext context)
  public virtual void Rollback(IEnumerable<PostExportInfo> exportableObjects,
                               ExportContext context)
```

### 2.3 Workspace view / editor

```
VciEditorAddInProvider                  (abstract, protected ctor)
  public virtual VciWorkspaceViewAddInProvider GetVciWorkspaceViewAddInProvider()

VciWorkspaceViewAddInProvider           (abstract, protected ctor)
  public virtual IEnumerable<ContextMenuAddIn> GetContextMenuAddIns()
```

### 2.4 Workflow result and context objects

```
WorkflowReturnCode : enum { Success, Fail, Cancel }

WorkflowContext
  WorkflowExecutionResult WorkflowExecutionResult(WorkflowReturnCode code)
  WorkflowExecutionResult WorkflowExecutionResult(WorkflowReturnCode code, string feedbackMessage)
  IEngineeringObject Parent { get; }
  T GetService<T>()

WorkflowExecutionResult
  string             Message           { get; }
  WorkflowReturnCode WorkflowReturnCode{ get; }

ImportContext  { ImportArgs Args { get; } }        ImportArgs { Workspace CurrentWorkspace { get; } }
ExportContext  { ExportArgs Args { get; } }        ExportArgs { Workspace CurrentWorkspace { get; } }

PreImportInfo  { ImportAction ImportAction; IEnumerable<…> ImportSourceInfos; IEngineeringObject ImportTarget }
PostImportInfo { … + ImportStatus ImportStatus; IEngineeringObject ImportedObject }
PreExportInfo  { ExportAction ExportAction; IEngineeringObject ObjectToExport;
                 MappingFileInfoComposition Mappings; bool SetStatus(PreExportAddInStatus) }
PostExportInfo { … + ExportStatus ObjectExportStatus; PreExportAddInStatus PreExportAddInStatus }
PreExportRollbackInfo { ExportAction; ObjectToExport; Mappings; PreExportAddInStatus }
```

`WorkflowExecutionResult` is produced through `WorkflowContext`, not via a constructor.

---

## 3. Standalone Openness EXE (no add-in types at all)

A standalone application uses **none** of the above. It has a real `Main`, references only
the Engineering assemblies, and must bootstrap its own session — see
`assets/templates/Program.cs.template` and the `session-and-project` skill.

Two rules that are easy to get wrong:

1. The `AppDomain.AssemblyResolve` registration and any use of `Siemens.Engineering` types
   must live in **separate** methods, both marked
   `[MethodImpl(MethodImplOptions.NoInlining)]`, or the JIT may bind the Openness types
   before the resolver is installed.
2. **Never** call `Dispose()` on a `TiaPortalProcess` obtained from
   `TiaPortal.GetProcesses()` — in V21 that tears down the live TIA Portal instance.
   `GetCurrentProcess().Dispose()` is the safe, different case.

---

## 4. How to verify a member not listed here

`pwsh` cannot do reflection-only loading — use **Windows PowerShell**:

```powershell
# Resolve the install directory from the registry — never hard-code it (see sdk-layout.md §1).
$root = (Get-ItemProperty 'HKLM:\SOFTWARE\Siemens\Automation\_InstalledSW\TIAP21\Global').Path
$dir  = Join-Path $root 'PublicAPI\V21\net48'
[System.AppDomain]::CurrentDomain.add_ReflectionOnlyAssemblyResolve({
  param($s,$e)
  $n = (New-Object System.Reflection.AssemblyName $e.Name).Name
  $f = Join-Path $dir "$n.dll"
  if (Test-Path $f) { [System.Reflection.Assembly]::ReflectionOnlyLoadFrom($f) } else { $null }
})
$asm = [System.Reflection.Assembly]::ReflectionOnlyLoadFrom((Join-Path $dir 'Siemens.Engineering.AddIn.Base.dll'))
try   { $t = $asm.GetTypes() }
catch [System.Reflection.ReflectionTypeLoadException] { $t = $_.Exception.Types | Where-Object { $_ -ne $null } }
$t | Where-Object { $_.Name -match 'TypeNameFragment' } | ForEach-Object { $_.FullName }
```

Pitfalls:
- without the `ReflectionOnlyAssemblyResolve` handler, `ToString()` on members throws
  `FileLoadException` for unresolved dependent types
- `-like` treats a backtick as a wildcard escape, so generic names such as ``ActionItem`1``
  must be matched with `-match`
- `GetMethod(name, 'Public,NonPublic,…')` binds the wrong overload in PowerShell; use
  `GetMethods('Public,NonPublic,Instance,DeclaredOnly') | Where-Object Name -eq …`
- `Siemens.Engineering.Contract` is not in `PublicAPI\…\net48` and cannot be resolved —
  returning `$null` from the handler for it is harmless
