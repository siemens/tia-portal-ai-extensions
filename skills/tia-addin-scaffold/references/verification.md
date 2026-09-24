# Verification

You **cannot** execute TIA Portal from an agent session. Split verification into a part
that is machine-checkable and a part the user must perform.

## 1. Machine-checkable

```powershell
cd <SolutionDir>
dotnet restore <Solution>.slnx
dotnet build   <Solution>.slnx -c Debug
```

Check, in this order:

1. **Registry resolution** — the build prints `TiaPortalLocation = <path>`.
   Empty or missing means the `ValidateTiaPortalLocation` target fired; the target TIA
   version is not installed.
2. **Compiler result** — `0 Fehler` / `0 Errors`. Never report success without having read
   the actual output.
3. **Publisher result** (add-ins only) — the build output and
   `bin\Debug\publisher_log.txt` must end with:

   ```
    --> S U C C E E D E D <--
   ```

   The log also lists what was packaged (assembly, Id, ProductName, each permission, the
   PDB, the timeout values). Use it to confirm the permission set is the intended minimal
   one and not the template's "everything" list.
4. **Artefact** — `bin\Debug\<AssemblyName>.addin` exists with a current timestamp.
   Report the full path and the timestamp so the user can tell builds apart.

## 2. Known build failure modes

| Symptom | Cause | Action |
|---|---|---|
| `renaming ... failed: Permission denied`, locked `.dll`/`.addin` | Visual Studio, TIA Portal or a previous debug run holds the file | Find the holder (`devenv`, `MSBuild`, `Siemens.Engineering.AddIn.Loader.x64`) and `Stop-Process -Id <PID>`; ask before killing an IDE with possibly unsaved work |
| `TIA Portal V<n> was not found` | Target version not installed | List `HKLM\SOFTWARE\Siemens\Automation\_InstalledSW\TIAP*` and offer an installed version |
| `Unable to find package …` | Internal NuGet feed unreachable | Check `NuGet.Config` and the corporate proxy variables before touching project files |
| `PublisherTask failed unexpectedly`, `Microsoft.Bcl.AsyncInterfaces` FileLoadException | MSBuild/SDK assembly-load conflict | Clear `bin`, `obj`, stop MSBuild node processes, restore and rebuild in a clean process |
| `MSB3270` processor-architecture warning | Project `MSIL`/`x86` vs. AMD64 `PublicAPI` assemblies | Expected noise for a `net48` add-in; do not dismiss it if the platform target itself changed |
| `Engineering object '<X>k__BackingField' of type '…' should not be defined as field, property or as a static member` | The publisher rejects add-ins that keep Openness objects alive between executions. From V20 on, add-ins are **not** reloaded after each execution, so such members are never reinitialised. | Never store an `IEngineeringObject` (or anything holding one) in a field, auto-property or static. Read what you need inside the local scope and reduce it to plain data — `string`, `int`, a POCO — before returning it. This fails the **build**, not just the package. |

## 3. Handover spotcheck (add-in)

Always hand over a **numbered** spotcheck. Template:

1. Build: `cd <SolutionDir>; dotnet build <Solution>.slnx -c Debug`
2. Artefact: `<SolutionDir>\<Project>\bin\Debug\<AssemblyName>.addin`,
   expected timestamp `<timestamp>`
3. Register: copy the `.addin` into
   `%APPDATA%\Siemens\Automation\Portal V<n>\UserAddIns\` (per-user folder, **not**
   `<TIA>\AddIns\` under Program Files — that path does not exist), or alternatively use
   **Options → Add-Ins → Import** inside TIA Portal to place it there for you. Then start
   TIA Portal V`<n>`, open the **Add-Ins** task card on the right edge and activate
   `<AddInDisplayName>`
4. Click path: open a project → in `<the relevant tree/editor>` right-click
   `<the exact node type>` → `<AddInDisplayName>` → `<menu entry text>`
5. Expected: `<what the GUI must show>`.
   Must stay unchanged: `<what must not change>`
6. Report back: the copied **text** of the add-in log window and of any TIA Portal error
   dialog. Screenshots alone are not sufficient for diagnosis.

State explicitly which behaviour is expected to change and which must stay unchanged.

> **Keep in sync with the generated project README.** Step 4 above and its
> `## Usage` section describe the same click path. Write both in the same pass
> from the same interview answers, and when a menu text or attach point changes
> later, change both. A README that names a menu entry the code does not create
> is worse than no README.

## 4. Handover spotcheck (standalone exe)

1. Build as above; artefact `bin\Debug\<AssemblyName>.exe`
2. Precondition: the Windows user must be a member of the **`Siemens TIA Openness`** group,
   otherwise the session is refused by the Openness firewall
3. Run the exe with TIA Portal already open (tests the attach path) and once without it
   (tests the start path)
4. Report the console output verbatim

## 5. Version bumping

Bump the add-in version (`AddInVersion` and `Product/Version` in `Config.xml`) **whenever a
build is handed over for manual testing**, so the user can distinguish builds in the TIA
Portal add-in overview. A TIA major-version change is a breaking change and requires a
**major** bump.
