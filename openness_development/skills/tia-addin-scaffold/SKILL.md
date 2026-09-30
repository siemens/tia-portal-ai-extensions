---
name: tia-addin-scaffold
description: Creating a new TIA Portal Openness project from scratch — interviews the developer about the entry model (packaged add-in or standalone Openness EXE), and, only for a packaged add-in, its entry architecture (in-process or separate EXE entry point), attach point (project tree, devices & networks, project/global library, version control import/export, workflow) and options, then generates, builds and verifies the project. Use for requests like "create a TIA add-in", "new Openness project", "scaffold an add-in", "start a TIA Portal add-in project", "I need an Openness console app". This skill creates new projects only; migrating an existing add-in to another TIA Portal major version is outside its scope.
metadata:
  siemens-depends-on: "openness-base"
---

# TIA Portal Add-In Scaffolding

## Overview

Creates a new Openness project that builds, packages and is ready to debug. The Siemens
Visual Studio template is deliberately **not** used as-is: it is pinned to one TIA version
and one add-in kind, requests every available CAS permission, and carries a dead
`reg query` fallback target.

This skill is **interview-driven**. Ask, then generate — do not assume defaults for
decisions that change the produced code.

## Bundled resources

| File | Use |
|---|---|
| `references/entry-points.md` | **Pinned, reflection-verified** base classes, overridables and delegate signatures for every add-in kind |
| `references/sdk-layout.md` | Registry lookup, assembly names and paths, publisher schema, build integration |
| `references/verification.md` | Build check, known failure modes, handover spotcheck templates |
| `assets/templates/*.template` | File templates with `{{Placeholder}}` substitution |

## 🛑 Hard rules

1. **Never emit an Openness member that is not in `references/entry-points.md`.**
   If the user asks for a kind or member that is not listed, verify it by reflection first
   (procedure in section 4 of that file) and **extend the reference** — then generate.
   If it cannot be verified, say so and omit it. Do not guess an API name.
2. **Minimum TIA Portal version is V21.** Reject anything lower and re-ask.
3. **Never emit the template's "request everything" permission list.** Start minimal.
4. **Never store an Openness object in a field, property or static member.** From TIA
   Portal V20 on, add-ins are not reloaded between executions, so such members are never
   reinitialised — the publisher detects this and **fails the build**. Read what you need
   inside the local scope and reduce it to plain data before handing it on.
5. Product-facing strings (menu texts, message boxes, log output) are **German**.
   Identifiers, comments and file names stay **English**.
6. Do not report a successful build without having read the actual build output and,
   for add-ins, `publisher_log.txt`.
7. **Every scaffolded project gets a generated README in its solution root.**
   It is end-user documentation in English and is generated from the same
   answers as the code and the spotcheck — see generation step 4.

## Interview

Ask **one question at a time**, each with concrete choices and an explicit **default**.

A question marked **must ask** is asked *as its own question*, always. It is never
answered by inference from the user's phrasing, never pre-filled into the defaults table,
and never bundled with other fields into a single "is this all correct?" confirmation.
"Build me an add-in" does **not** answer Q2 — the user has to see the alternative and its
consequences before choosing. Questions **not** marked must ask may be skipped when the
request already states them; say which value was taken.

Open the interview by showing the defaults table below and offering
*"take all defaults"* — this covers the optional fields only. Then ask every **must ask**
question individually, plus any optional field the developer wants to change.

### Defaults at a glance

| # | Field | Default | Must ask |
|---|---|---|---|
| 1 | TIA Portal version | **V21** | no — fixed |
| 2 | Entry model | Packaged add-in | **yes** |
| 2a | Add-in entry architecture | In-process add-in | **yes** (packaged add-in only) |
| 3 | Attach point | — | **yes** (add-in only) |
| 4 | Selected object type(s) | `Project` | **yes** (context menus) |
| 5 | Documentation content | — | **yes** |
| 6 | Project name | — | **yes** |
| 7 | TIA access | `ReadWrite` | no |
| 8 | UnrestrictedAccess | `No` | no |
| 9 | Author | `git config user.name`, else the Windows user name | no |
| 10 | Description | the purpose sentence from Q5 | no |
| 11 | Add-In version | `V0.1` | no |
| 12 | Product name | = project name | no |
| 13 | Product Id | freshly generated GUID | no |
| 14 | Product version | `0.0.1.0` | no |
| 15 | Namespace | = project name | no |
| 16 | UI framework | none | no |
| 17 | Additional permissions | none beyond the UI framework implication | no |
| 18 | Code signing | none (commented placeholder) | no |
| 19 | Git | `git init` + baseline commit | no |

Fields 1 and 7–15 are exactly the fields of the Siemens
*"TIA Portal Add-In Project"* Visual Studio wizard, in the same order.

### Q1 — TIA Portal version *(fixed)*

**V21.** Do not ask. These skills support V21 and higher; the references and templates are
pinned to the V21 SDK layout.

Deviate only if the user explicitly names a higher version. In that case check what is
actually installed before accepting it:

```powershell
Get-ChildItem 'HKLM:\SOFTWARE\Siemens\Automation\_InstalledSW' |
  Select-Object -ExpandProperty PSChildName |
  Where-Object { $_ -like 'TIAP*' }
```

| Situation | Reaction |
|---|---|
| user says nothing about a version | use **21** silently |
| user names `>= 21` and it is installed | accept, set `{{TiaVersion}}` |
| user names `>= 21` but it is not installed | warn — the build will fail on this machine — and confirm |
| user names `< 21` | **reject**, explain that these skills support V21+, offer V21 |

Whatever is used, the numeric value goes into `{{TiaVersion}}`; the wizard's `V19` style
is display only.

### 🛑 Mandatory entry-point selection

This decision must be asked explicitly when the user has not already supplied it. Do not
infer the entry model from a request such as "create an add-in" or "create an EXE".
Q2 must contain exactly two choices: **Packaged add-in** and **Standalone Openness EXE**.
Do not include the Q2a architecture choices in Q2.

### Q2 — Entry model *(must ask)*

| Choice | Consequence |
|---|---|
| **Packaged add-in** — *default* | Ask Q2a before proceeding; it is discovered by TIA Portal and governed by `Config.xml` |
| **Standalone Openness EXE** | `Exe.csproj.template` + `Program.cs.template`; a real `Main` bootstraps its own TIA Portal session; no `Config.xml`, publisher, or add-in entry-point types |

### Q2a — Add-in entry architecture *(must ask when Q2 is packaged add-in)*

| Choice | Consequence |
|---|---|
| **In-process add-in** — *default* | `AddIn.csproj.template` + `Config.xml` + publisher target + provider classes; choose no UI, WinForms, or WPF in Q16 |
| **Add-in with separate EXE entry point** | thin add-in launcher plus a separate WPF application, embedded into the `.addin`; the add-in has no `Main`, while the application owns the executable entry point |

If the user is unsure, explain: the in-process add-in shares TIA Portal's AppDomain,
dispatcher, dependency graph, and crash domain. The separate-EXE add-in only extracts
and starts the application; the application reattaches to the calling TIA Portal process
by process id and is additionally governed by the Openness firewall and the
`Siemens TIA Openness` Windows group.

If Q2 selects **Standalone Openness EXE**, do not ask Q2a, Q3, or Q4. Use Q5 for the
application's runtime behavior instead of context-menu entries. Q7, Q8, Q11-Q14, Q17,
and Q18 are add-in-only configuration questions; use their defaults for any executable
metadata needed by the EXE template without asking them. Q6, Q9, Q10, Q15, Q16, and Q19
still apply.

### Q3 — Attach point *(must ask, add-in only, multi-select)*

| Choice | Base class |
|---|---|
| Project tree context menu | `ProjectTreeAddInProvider` |
| Devices & networks context menu | `DevicesAndNetworksAddInProvider` |
| Project library tree context menu | `ProjectLibraryTreeAddInProvider` |
| Global library tree context menu | `GlobalLibraryTreeAddInProvider` |
| Version control — import | `VciImportAddInProvider` |
| Version control — workspace repository / export | `VciWorkspaceRepositoryAddInProvider` |
| Version control — workspace view / editor | `VciEditorAddInProvider` |

Several may be combined; generate one provider class per attach point.

### Q4 — Selected object type(s) *(must ask for context menus)*

Determines the `AddActionItem<T>` type arguments **and** which Engineering
assemblies must be referenced (see
[the entry-point reference](references/entry-points.md)).
Default `Project`; common alternatives `Device`, `DeviceItem`, `PlcSoftware`.
Up to three types can be combined via the `AddActionItem<T1,T2,T3>` overloads.

### Q5 — Documentation *(must ask)*

For an add-in, ask this **after** Q3/Q4 so the click paths are already concrete. For a
standalone EXE, ask it after Q2 and describe how the application is started, what it does
at runtime, and what the user sees. In both cases, collect three things:

1. **Purpose** — one or two sentences a plant engineer understands: what the add-in or
   application does *for them*, not how it is built.
2. **Per entry behaviour** — for an add-in, describe every menu entry from Q3/Q4: what
   happens when it is clicked, and what the user sees afterwards. For a standalone EXE,
   describe the startup path, runtime behavior, and resulting output or UI.
3. **Known limitations** — anything the user must know up front (object types that are
   ignored, states in which the entry is greyed out, changes that are not undoable).

If the user has nothing to add for 3, omit the section rather than writing "none".
Answer 1 is the default for the `Description` field (Q10).

### Q6 — Project name *(must ask)*

Used for the solution folder, the `.slnx`, the `.csproj` and `AssemblyName`. It is also
the default for *Product name* (Q12) and *Namespace* (Q15).

| Situation | Reaction |
|---|---|
| contains spaces or `.` | warn — the assembly name inherits it; offer a stripped variant, keep the original as *Product name* |
| not a valid C# identifier after stripping | ask again |
| a folder of that name already exists | stop and ask; never scaffold into a non-empty folder |

### Q7 — TIA access

`ReadWrite` *(default)* or `ReadOnly` — renders as exactly one child of `TIAPermissions`
in `Config.xml`: `<TIA.ReadWrite />` or `<TIA.ReadOnly />`.

Recommend `ReadOnly` when the answers to Q5 describe only reading, reporting or
exporting. `ReadOnly` is enforced by TIA Portal: a write through Openness throws at
runtime, so an over-restrictive choice fails loudly rather than silently.

### Q8 — UnrestrictedAccess

`No` *(default)* or `Yes`.

`RequiredPermissions` in the publisher schema is a **choice**: an add-in declares either
`SecurityPermissions` (a list of individual permissions) **or** `UnrestrictedPermissions`
— never both.

| Answer | Reaction |
|---|---|
| `No` | render the `SecurityPermissions` branch from Q17 |
| `Yes` | render the `UnrestrictedPermissions` branch, **discard** the individual permission list from Q17, and say so explicitly |

On `Yes`, a `JustificationComment` of **10 to 120 characters** is mandatory — the
publisher rejects the package otherwise. Ask for it; do not invent one. State that the
comment is visible to whoever reviews the add-in before activating it.

Push back once before accepting `Yes`: unrestricted access removes the sandbox for the
whole add-in. Accept it if the user confirms — do not argue twice.

### Q9 — Author

Default: `git config user.name` in the target folder, falling back to the Windows user
name (`$env:USERNAME`). Never write the wizard's literal `My Name`.

```powershell
(git config user.name) 2>$null | ForEach-Object { $_ }   # empty if git is not configured
```

Free text; appears in `Config.xml` and in the README footer.

### Q10 — Description

Default: the purpose sentence from Q5. One sentence, product-facing.

Written **German** in the product where the user sees it, but the `Config.xml`
`<Description>` and the README follow the language rules in the hard rules section:
the README is English, the menu texts are German.

### Q11 — Add-In version

Default `V0.1` — the wizard's convention. Free-form string; the schema puts no pattern on
`AddInVersion`. This is the version of the *add-in*, shown in TIA Portal.

Do **not** reuse this value for *Product version* (Q14) — the `V` prefix violates the
product version pattern.

### Q12 — Product name

Default: the project name. This is the string TIA Portal shows in **Options → Add-Ins**,
so it may contain spaces and mixed case.

Never derive the assembly name or the namespace from it — those come from Q6 and Q15.

### Q13 — Product Id

Default: a freshly generated GUID.

```powershell
[guid]::NewGuid().ToString()
```

Show the generated value to the developer instead of hiding it. Reject the wizard's
all-zero GUID `00000000-0000-0000-0000-000000000000` — it identifies the add-in for
TIA Portal and must be unique per product, stable across versions.

### Q14 — Product version

Default `0.0.1.0`. Must match `^(\d+\.)?(\d+\.)?(\d+\.)?(\d+)$` — digits and dots only,
one to four parts.

| Answer | Reaction |
|---|---|
| matches the pattern | accept |
| starts with `V`, or contains a suffix like `-beta` | **reject** with the pattern, offer the digits-only form |

### Q15 — Namespace

Default: the project name. Feeds `{{RootNamespace}}` in the `.csproj` and the `namespace`
declaration of every generated `.cs` file.

Must be a valid C# namespace (identifier parts separated by `.`). If it is not, say why
and ask again.

### Q16 — UI framework *(in-process add-in or standalone EXE only)*

| Choice | `{{ProjectSdk}}` | `{{UiFrameworkProperties}}` |
|---|---|---|
| none — *default* | `Microsoft.NET.Sdk` | *(empty)* |
| WinForms | `Microsoft.NET.Sdk.WindowsDesktop` | `<UseWindowsForms>true</UseWindowsForms>` |
| WPF | `Microsoft.NET.Sdk.WindowsDesktop` | `<UseWpf>true</UseWpf>` |

A UI framework implies the `System.Security.Permissions.UIPermission` entry in
`Config.xml` for an in-process add-in. A message box in a click handler already counts as
UI — if Q5 describes a dialog, WinForms is the smaller choice. For a standalone EXE, the
choice controls the executable project and does not add an add-in permission entry.

When Q2a selected **Add-in with separate EXE entry point**, skip Q16's in-process
framework choice. The application is a separate WPF `WinExe`; the add-in remains a
thin non-UI launcher. Ask instead:

1. **Application purpose and window behavior** — what the engineer does in the window
   and what is shown after it opens.
2. **Selected data passed to the application** — pass only quoted strings such as
   process id, selected object names, menu identifier, and additional arguments; never
   pass Openness object references.

The separate-executable design requires
`Siemens.Engineering.AddIn.Permissions.ProcessStartPermission`,
`System.Security.Permissions.EnvironmentPermission`, and
`System.Security.Permissions.FileIOPermission` in `Config.xml`. The latter two are
required because the launcher reads the temporary-directory environment variables and
extracts the embedded application to disk; see `references/packaged-exe.md`.
Keep all Openness access in the application's view-model/access layer; the WPF window
code-behind must not name an Openness type before the application's resolver is
initialized. Use `references/packaged-exe.md` for the process-boundary contract, extraction,
reattachment, firewall, and embedding rules.

### Q17 — Additional permissions *(packaged add-in only)*

Default: nothing beyond `UIPermission` when Q16 chose a UI framework. Ask whether the
add-in needs file access, process start, network or registry, and add only those.

Ignored entirely when Q8 was answered `Yes`.

### Q18 — Code signing *(packaged add-in only)*

Default: **none** — emit the `Certificates` block commented out as a placeholder.
Present this as an **open point**: the V21 publisher schema makes signing optional, but
whether TIA Portal V21 loads an unsigned `.addin` without extra user consent is not
confirmed. If the user has a certificate, ask for `SigningCertificateThumbprint` or the
`.pfx` path.

### Q19 — Git

Default: `git init` locally with a `.gitignore` from the template and a baseline commit.
Local only — never add a remote, push or tag without an explicit request.

## Reacting to the answers

| Situation | Reaction |
|---|---|
| answer is empty, `-`, "default" or "whatever" | take the default and **state which value was used** |
| "take all defaults" | apply every default, then **still ask each must-ask question individually** |
| a must-ask answer seems implied by the request | ask anyway, showing the alternatives — an implied answer is not a given answer |
| project name contains spaces | strip them for the project/assembly/namespace, keep the original as *Product name* |
| product version has a `V` prefix or a text suffix | reject, quote the pattern, propose the digits-only form |
| `AddInVersion` and *Product version* given as the same value | accept both but point out they are different fields with different formats |
| UnrestrictedAccess `Yes` without a justification comment | do not generate — ask for the comment first |
| justification comment shorter than 10 or longer than 120 characters | reject with the actual length, ask again |
| namespace is not a valid C# identifier | reject, propose a sanitised variant |
| product Id given as the zero GUID | reject, generate a real one and show it |
| `ReadOnly` chosen but Q5 describes writing | point out the contradiction once, then follow the user's choice |
| a value is only needed for the other hosting model | skip the question and say why |

## Generation procedure

1. Create the layout:

   ```
   <SolutionDir>\
     <ProjectName>.slnx
     README.md
     .gitignore
     <ProjectName>\
       <ProjectName>.csproj
       Config.xml                        (add-in only)
       Properties\launchSettings.json    (add-in only)
       .vscode\tasks.json, launch.json
       <entry point .cs files>
   ```

2. Copy the templates and substitute the placeholders:

   | Placeholder | Value |
   |---|---|
   | `{{ProjectName}}` | Q6 — folder, `.csproj`, `AssemblyName` |
   | `{{RootNamespace}}` | Q15 (wizard field *Namespace*) |
   | `{{TiaVersion}}` | Q1, digits only — `21` |
   | `{{ProjectSdk}}` / `{{UiFrameworkProperties}}` | Q16 |
   | `{{OutputType}}` | `Exe` (console) or `WinExe` (GUI), exe template or separate application only |
   | `{{Author}}` | Q9 |
   | `{{Description}}` | Q10 |
   | `{{Company}}`, `{{Copyright}}` | Q9 unless given separately |
   | `{{AddInVersion}}` | Q11 — free-form, default `V0.1` |
   | `{{ProductName}}` | Q12 — default = `{{ProjectName}}`, may contain spaces |
   | `{{ProductId}}` | Q13 — freshly generated GUID |
   | `{{ProductVersion}}` | Q14 — digits and dots only, default `0.0.1.0` |
   | `{{TiaPermission}}` | Q7 — `TIA.ReadWrite` or `TIA.ReadOnly` |
   | `{{PermissionsBlock}}` | Q8/Q17 — the `SecurityPermissions` **or** the `UnrestrictedPermissions` element, never both |
   | `{{CertificatesBlock}}` | Q18 |
   | `{{AdditionalEngineeringReferences}}` | derived from Q4 (`Siemens.Engineering.Step7` etc.) |
   | `{{UsageSection}}` / `{{NotesSection}}` / `{{AdditionalRequirements}}` | Q5, see step 4 |

   `{{PermissionsBlock}}` renders as exactly one of these two — the publisher schema
   declares them as a choice, emitting both makes the package invalid:

   ```xml
   <SecurityPermissions>
     <!-- Only the permissions actually used by this Add-In are requested.
          Add further entries individually when a feature needs them:
            System.Security.Permissions.UIPermission
            System.Security.Permissions.FileIOPermission
            System.Security.Permissions.FileDialogPermission
            System.Security.Permissions.RegistryPermission
            System.Security.Permissions.EnvironmentPermission
            System.Security.Permissions.SecurityPermission.UnmanagedCode
            Siemens.Engineering.AddIn.Permissions.ProcessStartPermission
            System.Net.WebPermission / System.Net.SocketPermission
          See Siemens.Engineering.AddIn.Publisher.xsd for the complete list. -->
     <System.Security.Permissions.UIPermission />
   </SecurityPermissions>
   ```

   ```xml
   <UnrestrictedPermissions>
     <System.UnrestrictedAccess>
       <JustificationComment>…10 to 120 characters…</JustificationComment>
     </System.UnrestrictedAccess>
   </UnrestrictedPermissions>
   ```

   Leave no `{{…}}` in the generated output — an unsubstituted placeholder is a bug.

3. Write the entry-point C# **strictly from `references/entry-points.md`**:
   - one `public sealed class` per provider, overriding the documented `Get…` method
   - one `ContextMenuAddIn` subclass per menu, `protected override void BuildContextMenuItems`
   - wrap every click handler body in `try/catch` — the V21 `AddActionItem` overloads no
     longer take an error-handler delegate
   - German menu texts and messages
   - for the add-in with separate EXE entry point choice, keep the add-in handler thin: extract the embedded
     application, pass the fixed ordered quoted-string contract, and call
     `Siemens.Engineering.AddIn.Utilities.Process.Start`; do not put business logic in it

4. For the add-in with separate EXE entry point choice, add the application and packaging projects before
   writing the README:
   - a WPF `WinExe` application and a non-WPF view-model/access project targeting `net48`
   - a project reference from the add-in with `ReferenceOutputAssembly=false`
   - an MSBuild target that builds the application, zips its output, and embeds the zip as
     a manifest resource named `<ProjectName>.App.zip`
   - `ProcessStartPermission`, `EnvironmentPermission`, and `FileIOPermission` in `Config.xml`
   - the application startup/reattachment contract from `references/packaged-exe.md`

5. Write the generated project README into the **solution root** — always, it is
   not optional. Use
   `assets/templates/README.AddIn.md.template` for both packaged choices, or
   `README.Exe.md.template` only for the standalone mode selected in Q2.
   It is written **after** the entry-point code exists, so that every menu text can be
   quoted from the actual source instead of from the interview notes.

   | Section | Content |
   |---|---|
   | `{{UsageSection}}` | One `###` heading per menu entry, each with the **full click path** and what the user sees afterwards. For the add-in with separate EXE entry point choice, state that the add-in opens a separate taskbar window and describe the first Openness firewall prompt. |
   | `{{NotesSection}}` | Q5 limitations, as a bullet list. Omit the whole `## Notes and limitations` heading if there are none. |
   | `{{AdditionalRequirements}}` | Extra bullets only if Q17 added permissions with a user-visible precondition (e.g. write access to a directory). Otherwise remove the line. |

   Rules for the README:
   - **English**, addressed to the person *using* the add-in, not to a developer.
     No build instructions, no API names, no class or file names.
   - Menu texts and dialog captions are **German** in the product and must be quoted
     **verbatim in German**, inside the English sentence — never translate them.
   - Click paths in the README and in the handover spotcheck
     (`references/verification.md` §3/§4) describe the same thing and must be written in
     one pass from the same answers. If either is changed later, change both.
   - The generated project README is a repository artefact; the publisher does
     not pack it into the `.addin`. Do not add it to `Config.xml`.

   Example of one `{{UsageSection}}` entry:

   ```markdown
   ### Show project information

   Right-click the project node at the top of the project tree and choose
   **{{ProjectName}} → "Projektinformationen anzeigen"**.
   A dialog opens showing the project name and the storage path of the open project.
   Close it with **OK**; nothing in the project is changed.
   ```

6. Verify per `references/verification.md`: restore, build, read the output, read
   `publisher_log.txt`, confirm the `.addin` timestamp.

7. If Q19 was accepted, commit with a conventional message
   (`chore: scaffold <ProjectName> TIA Portal V<n> add-in`).

7. Hand over the numbered spotcheck from `references/verification.md` §3 or §4.

## Extending this skill

Adding a **new add-in kind** requires exactly three edits:

1. Verify its base class and overridables by reflection (procedure in
   `references/entry-points.md` §4) and add a section there.
2. Add the option to Q3 above.
3. Only if its project layout differs: add a template under `assets/templates/`.
4. Make sure the kind produces a usable `{{UsageSection}}` entry — a click path a user can
   follow. A kind that cannot be described that way is not finished.

Moving to a **new TIA major version** (e.g. V22):

1. Update `references/sdk-layout.md` — paths, assembly names, publisher schema changes.
2. Re-run the reflection procedure against the new `PublicAPI\V<n>\net48` and update
   `references/entry-points.md` where signatures changed.
3. Nothing in the templates changes except the `{{TiaVersion}}` value the interview supplies.

Do **not** add new build, lint or test tooling to generated projects unless asked.
