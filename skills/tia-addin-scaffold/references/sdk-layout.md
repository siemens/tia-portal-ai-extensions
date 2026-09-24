# TIA Portal Openness SDK Layout (V21 baseline)

Everything below was verified against a real TIA Portal **V21** installation, whose
directory is read from the registry (section 1) rather than assumed — it is not always
the default `%ProgramFiles%\Siemens\Automation\Portal V<n>`.
`<n>` denotes the TIA major version.
A V22 bump should require edits only in this file and in the templates' `TiaVersion`.

## 1. Locating the installation

**Never probe the filesystem.** Read the registry:

```
HKEY_LOCAL_MACHINE\SOFTWARE\Siemens\Automation\_InstalledSW\TIAP<n>\Global
    Path  =  <install directory>
```

Check both `RegistryView.Registry64` and `RegistryView.Registry32`.
Installed versions can be enumerated by listing the subkeys of `…\_InstalledSW\`
(`TIAP12`, `TIAP20`, `TIAP21`, …) — use this to offer the user real choices.

MSBuild form used by the templates:

```xml
<TiaPortalLocation Condition="'$(TiaPortalLocation)' == ''">$([MSBuild]::GetRegistryValueFromView('HKEY_LOCAL_MACHINE\SOFTWARE\Siemens\Automation\_InstalledSW\TIAP$(TiaVersion)\Global', 'Path', '', RegistryView.Registry64, RegistryView.Registry32))</TiaPortalLocation>
```

> The Siemens VS template additionally reads `…\TIAP<n>\EditionMain` and has an
> `Exec`+`reg query`+`ReadLinesFromFile` fallback that writes `TiaPortalLocation.log` into
> the output folder. Both keys carry the same `Path` value. **Drop the fallback** — it is
> dead weight and produces a stray log file.

## 2. Directory layout

| Content | Path |
|---|---|
| API assemblies | `<TIA>\PublicAPI\V<n>\net48\` |
| Publisher | `<TIA>\PublicAPI\V<n>\Siemens.Engineering.AddIn.Publisher.exe` |
| Publisher schema | `<TIA>\PublicAPI\V<n>\Siemens.Engineering.AddIn.Publisher.xsd` |
| Import/export XSDs | `<TIA>\PublicAPI\V<n>\Schemas\` |
| HW parameter description | `<TIA>\PublicAPI\V<n>\HW Parameter description\` |
| DebugStarter | `<TIA>\Bin\PublicAPI\AddIn\EasyAddIn\Siemens.Engineering.AddIn.DebugStarter.exe` |
| Add-in host / loader | `<TIA>\Bin\PublicAPI\AddIn\Host\`, `…\Loader\` (`…Loader.x64.exe`) |
| Installed add-ins (per-user) | `%APPDATA%\Siemens\Automation\Portal V<n>\UserAddIns\` |

> ⚠️ **The install folder is per-user, not under the TIA Portal program directory.**
> `<TIA>\AddIns\` (under `%ProgramFiles%\...`) does **not** exist / is not where TIA Portal
> looks for add-ins to activate. Copy the `.addin` file into
> `%APPDATA%\Siemens\Automation\Portal V<n>\UserAddIns\` instead — e.g.
> `C:\Users\<user>\AppData\Roaming\Siemens\Automation\Portal V21\UserAddIns\<AssemblyName>.addin`.
> Alternatively, skip the manual copy entirely and use TIA Portal's own **Options → Add-Ins**
> task card, which has an **Import** action that copies the selected `.addin` file into this
> same per-user folder for you. Both routes end up in the same location and both still
> require activating the add-in afterwards in **Options → Add-Ins**.

> ⚠️ **Pre-V21 layout differs.** V19 used a single `PublicAPI\V19.AddIn\` folder that held
> both the add-in assemblies *and* the publisher *and* the DebugStarter. Any project
> carried over from V19/V20 will have wrong paths in `.csproj` **and** in
> `Properties\launchSettings.json`.

## 3. Assemblies

### Add-in assemblies (`PublicAPI\V<n>\net48\`)

| Assembly | Purpose |
|---|---|
| `Siemens.Engineering.AddIn.Base.dll` | **all** add-in entry-point types (providers, menus, VCI, workflow) |
| `Siemens.Engineering.AddIn.Utilities.dll` | helper utilities |
| `Siemens.Engineering.AddIn.Permissions.dll` | `ProcessStartPermission` etc. |
| `Siemens.Engineering.AddIn.Step7.dll` | Step7-specific add-in extensions |
| `Siemens.Engineering.AddIn.Safety.dll` | safety-specific add-in extensions |

> ⚠️ **Renamed in V21:** `Siemens.Engineering.AddIn.dll` → `Siemens.Engineering.AddIn.Base.dll`.
> This is the single most common break when migrating a pre-V21 add-in.

### Engineering assemblies (same folder)

`Siemens.Engineering.Base`, `.Step7`, `.Startdrive`, `.Safety`, `.SafetyValidation`,
`.DCC`, `.CFC`, `.WinCC`, `.WinCC.Extension`, `.WinCCUnified`, `.TeamcenterGateway`.

Reference them with `<Private>False</Private>` and `<SpecificVersion>False</SpecificVersion>` —
they must **not** be copied to the output directory.

### Modular assemblies since V21

Before V21 a single machine-specific `Siemens.Engineering.dll` was generated from the
installed packages, so referencing a class from a package the customer never installed
threw `TypeLoadException` at runtime. Since V21 each package ships its own assembly:

- reference only what you actually use
- opening a project whose packages are missing throws **`MissingProductsException`**
- *attaching* to such a project throws nothing — the compositions are silently **empty**,
  so check explicitly instead of assuming a non-null project is usable

### LTS

A TIA version supports its own API plus three previous LTS APIs. The LTS chain was
restarted once in V21 for security reasons; from V21 onward the rolling model resumes.
An add-in built against V21 does **not** load in V19/V20.

## 4. Publisher configuration (`Config.xml`)

Namespace: `http://www.siemens.com/automation/Openness/AddIn/Publisher/V<n>` — the
namespace encodes the schema version and must match the target TIA version.

Element order is enforced by `xs:all`/`xs:sequence`; the V21 schema accepts:

| Element | Required | Notes |
|---|---|---|
| `Author` | no | |
| `Description` | no | |
| `AddInVersion` | no | free-text, e.g. `V1.0` |
| `Product` | **yes** | `Name` (non-empty), `Id` (GUID), `Version` matching `^(\d+\.)?(\d+\.)?(\d+\.)?(\d+)$` |
| `FeatureAssembly` | **yes** | `AssemblyInfo` → `Assembly`, optional `Pdb` |
| `AdditionalAssemblies` | no | further `AssemblyInfo` entries shipped in the package |
| `RequiredPermissions` | **yes** | see below |
| `Certificates` | no | `SigningCertificate` **or** `SigningCertificateThumbprint`, plus `AdditionalCertificates` |
| `DisplayInMultiuser` | no | |
| `AddInTimeoutConfiguration` | no | `ActivationTimeout` 2000–10000 ms, `ContextMenuTimeout` 200–10000 ms |

`RequiredPermissions`:
- `TIAPermissions` — **exactly one** of `TIA.ReadOnly` / `TIA.ReadWrite`
- then **either** `SecurityPermissions` (individual CAS permissions) **or**
  `UnrestrictedPermissions` → `System.UnrestrictedAccess` with a
  `JustificationComment` of 10–120 characters

Available `SecurityPermissions` elements (all optional, each may carry a `Comment`):
`System.Configuration.ConfigurationPermission`, `System.Data.Odbc.OdbcPermission`,
`System.Data.OleDb.OleDbPermission`, `System.Data.SqlClient.SqlClientPermission`,
`System.Diagnostics.EventLogPermission`, `System.Drawing.Printing.PrintingPermission`,
`System.Net.Mail.SmtpPermission`, `System.Net.NetworkInformation.NetworkInformationPermission`,
`System.Net.SocketPermission`, `System.Net.WebPermission`,
`System.Security.Permissions.EnvironmentPermission`, `…FileDialogPermission`,
`…FileIOPermission`, `…IsolatedStorageFilePermission`, `…KeyContainerPermission`,
`…RegistryPermission`, `…StorePermission`, `…UIPermission`, `…WebBrowserPermission`,
`…MediaPermission`, `…SecurityPermission.UnmanagedCode`,
`Siemens.Engineering.AddIn.Permissions.ProcessStartPermission`.

> The Siemens VS template requests **every** permission. Always start from the minimum
> the generated features actually need and keep the rest as a comment.

**Signing** is optional per schema. Whether TIA Portal V21 loads an *unsigned* `.addin`
without extra user consent is **not confirmed here** — present it to the user as an open
point rather than a settled default.

### 4.1 Mapping to the Visual Studio wizard fields

The Siemens *"TIA Portal Add-In Project"* wizard collects exactly these values.
The interview in the [scaffold skill](../SKILL.md) mirrors them one-to-one, so a
developer who knows the wizard recognises the questions.

| Wizard field | Wizard default | Config.xml target |
|---|---|---|
| TIA version | `V19` | publisher namespace + SDK paths |
| TIA access | `ReadWrite` | `RequiredPermissions/TIAPermissions/TIA.ReadWrite` |
| UnrestrictedAccess | `No` | `SecurityPermissions` vs. `UnrestrictedPermissions` branch |
| Author | `My Name` | `Author` |
| Description | `The Add-In description.` | `Description` |
| Add-In version | `V0.1` | `AddInVersion` |
| Product name | `Add-In Name` | `Product/Name` |
| Product Id | zero GUID | `Product/Id` |
| Product version | `0.0.1.0` | `Product/Version` |
| Namespace | *(empty)* | `RootNamespace` in the `.csproj`, not in `Config.xml` |

Two traps in this mapping:

1. **`AddInVersion` and `Product/Version` are different fields with different formats.**
   `AddInVersion` is free text (`V0.1`); `Product/Version` must match
   `^(\d+\.)?(\d+\.)?(\d+\.)?(\d+)$`, so a `V` prefix or a `-beta` suffix is rejected by
   the publisher.
2. **`Product/Name` is not the assembly name.** It is the display string in
   **Options → Add-Ins** and may contain spaces; the assembly name comes from the project
   name. `FeatureAssembly/Assembly` must stay `<AssemblyName>.dll`.

The zero GUID from the wizard is a placeholder, not a valid value — generate a real one
and keep it stable across versions of the same product.

## 5. Build integration

Publish step (runs after the build, produces `<AssemblyName>.addin` next to the DLL):

```xml
<Target Name="PublishAddin" AfterTargets="Build">
  <Exec Command="&quot;$(TiaAddInPublisher)&quot; -f &quot;$(ProjectDir)$(OutDir)Config.xml&quot; -v -c -l &quot;$(ProjectDir)$(OutDir)publisher_log.txt&quot;" />
</Target>
```

`Config.xml` must be a `Content` item with `CopyToOutputDirectory=PreserveNewest`,
because the publisher reads the **copy in the output folder**.

Project settings that matter:
- `net48` — mandatory
- `Microsoft.NET.Sdk.WindowsDesktop` + `UseWindowsForms`/`UseWpf` only when a UI is needed;
  plain `Microsoft.NET.Sdk` otherwise
- `AppendTargetFrameworkToOutputPath=false` — keeps the output at `bin\<Config>\`, which the
  publisher path and `launchSettings.json` assume
- `GenerateTargetFrameworkAttribute=false` — as in the Siemens template

## 6. Debugging

`Properties\launchSettings.json`:

```json
{
  "profiles": {
    "Debug TIA Portal Add-In": {
      "commandName": "Executable",
      "executablePath": "$(TiaPortalLocation)\\Bin\\PublicAPI\\AddIn\\EasyAddIn\\Siemens.Engineering.AddIn.DebugStarter.exe",
      "commandLineArgs": "$(ProjectDir)$(OutDir)<AssemblyName>.addin"
    }
  }
}
```

The add-in runs inside `Siemens.Engineering.AddIn.Loader.x64.exe`, not inside
`Siemens.Engineering.exe`; the VS Code `launch.json` therefore attaches to the
DebugStarter **and** to several add-in host processes.
