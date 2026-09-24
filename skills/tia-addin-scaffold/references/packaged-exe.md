# Packaged Add-In with Separate EXE

This is the out-of-process packaged-add-in option. It is distinct from a
standalone Openness executable:

- the packaged add-in is discovered by TIA Portal and has no `Main`;
- the separate WPF application owns the executable entry point;
- the add-in is governed by `Config.xml`;
- the application is additionally governed by the Openness firewall and the
  local `Siemens TIA Openness` Windows group.

## Process boundary

Only strings cross the boundary. The add-in must not pass Openness objects to
the application. It must pass a fixed, ordered set of quoted string values:
the calling TIA Portal process identity, the selected object names, the
selected menu identity, and any optional additional data. The runtime supplies
the executable path as the first command-line value; the application must keep
the remaining values in their documented order.

Optional values must still be emitted as empty strings so later values do not
shift position. Reject or escape selected names and other values containing
double quotes before starting the application.

**Read the complete command line with `Environment.GetCommandLineArgs()`, never
with WPF's `StartupEventArgs.Args` (`e.Args` in `OnStartup`).** `e.Args`
excludes the executable path, so using it changes the expected positional
contract and can feed the wrong value into process selection, producing a
confusing `Die TIA Portal Prozess-ID ist ungueltig` / `ArgumentException` deep
inside the attach call.

The add-in must use the verified
`Siemens.Engineering.AddIn.Utilities.Process.Start` API, not
`System.Diagnostics.Process`, because the add-in runs under the TIA Portal
add-in sandbox. The click handler starts the application and returns without
waiting.

## Add-in launcher

The launcher performs only these steps:

1. Find the embedded resource whose name ends with `<ProjectName>.App.zip`.
2. Extract it below `%TEMP%\<ProjectName>.App`, using a GUID-suffixed fallback
   if an existing running copy cannot be deleted.
3. Find the extracted `.exe`.
4. Start it with the fixed ordered argument contract above.

Extraction is lazy and occurs on the first click, not while TIA Portal loads
the add-in. Missing resources and missing executables must surface as German
errors listing the resource names or extraction path. Never use a broad empty
catch.

The add-in must request
`Siemens.Engineering.AddIn.Permissions.ProcessStartPermission`. If the add-in
has a UI of its own, request `UIPermission` separately. Keep the permission set
minimal.

**Extraction requires two more permissions, confirmed at runtime** — the
add-in sandbox denies these by default and the resulting `SecurityException`
surfaces from deep inside `Lazy<T>`/`ExtractApp`, which makes the true cause
easy to miss:

| Permission | Why it is needed |
|---|---|
| `System.Security.Permissions.EnvironmentPermission` | `Path.GetTempPath()` demands it just to read the `%TEMP%`/`%TMP%` environment variables — this is the first call the launcher makes and fails immediately without it. |
| `System.Security.Permissions.FileIOPermission` | Creating the extraction directory and writing the extracted `.exe` under `%TEMP%\<ProjectName>.App` needs file I/O rights, not just the environment lookup. |

Request both alongside `ProcessStartPermission` whenever the launcher extracts
an embedded application to disk — this is not optional for this pattern, even
though it is not implied by `ProcessStartPermission` itself.

## Application startup and reattachment

The application is a normal WPF `WinExe` targeting `net48`. Keep the WPF
window code-behind free of Openness types. Initialize the Openness resolver
before touching any Openness type, then:

1. Read the command-line arguments.
2. Resolve the TIA Portal process identity from the first application argument.
3. Select the matching process from `TiaPortal.GetProcesses()` by id.
4. Attach to that process asynchronously so the UI thread stays responsive.
5. Bring the application window forward after initialization.

Do not attach to `GetProcesses().First()`, and never dispose a
`TiaPortalProcess` obtained from `GetProcesses()`; disposing such a handle can
tear down the live TIA Portal instance. The application may keep a direct-start
debug path, but it must not weaken the add-in-started process-id path.

**On first use, the Openness firewall prompt appears inside TIA Portal.** Do
not create or show the application's main window before attach has completed
— an empty or half-populated window sitting in front of TIA Portal hides the
prompt and reads as a hang. Verified startup sequence:

1. In `OnStartup`, install the assembly resolver, then set
   `ShutdownMode = ShutdownMode.OnExplicitShutdown` and start the attach as a
   fire-and-forget async method. Create **no window yet**.
2. Before calling `Attach()`, resolve the process-identity argument to a process id with
   `System.Diagnostics.Process.GetProcessById` and call the plain Win32
   `SetForegroundWindow` on its `MainWindowHandle` (a small `DllImport`
   helper with no Openness types, safe to call before the resolver has loaded
   any Openness assembly). This brings TIA Portal — and the firewall dialog,
   if it appears — to the front while nothing else is on screen yet.
3. Await the attach. It blocks until the user resolves any firewall
   dialog, then returns (or throws if TIA Portal or the process is gone).
4. Only after attach succeeds, construct the window with the already-attached
   session, set `ShutdownMode = ShutdownMode.OnMainWindowClose`, and show it.
5. If attach throws, show one German error message box and shut down; never
   leave a blank window open waiting for a connection that already failed.

The user must also belong to the `Siemens TIA Openness` group; mention this in
the error path if attach fails for an unclear reason.

## Project and packaging shape

Use one solution with these projects:

```text
<ProjectName>\
  <ProjectName>.csproj                 # packaged add-in and launcher
<ProjectName>.App\
  <ProjectName>.App.csproj             # WPF WinExe
<ProjectName>.ViewModels\
  <ProjectName>.ViewModels.csproj      # non-WPF access/view-model layer
```

The add-in references the application project with
`ReferenceOutputAssembly=false`. A build target must build the application,
zip its output, and add the zip as an embedded resource with logical name
`<ProjectName>.App.zip`. The add-in must not reference the application's output
assembly for compilation.

The view-model/access project may use the verified Siemens Collaboration.Net
packages when that MVVM stack is selected. Do not invent package versions or
members: verify them against the installed SDK/package references before
generating source. Keep `Siemens.Engineering` access out of the WPF view layer.

## Verification

In addition to the normal add-in checks:

- confirm the build log reports the application zip was embedded;
- confirm the add-in manifest contains the `<ProjectName>.App.zip` resource;
- confirm `publisher_log.txt` contains `ProcessStartPermission` and ends with
  `--> S U C C E E D E D <--`;
- perform one run with TIA Portal already open and one first-run firewall
  approval;
- confirm the application appears as a separate taskbar window and attaches
  to the selected TIA Portal process.
