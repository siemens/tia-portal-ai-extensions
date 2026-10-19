---
name: openness-testing
description: Live TIA Portal Openness integration-test and CI guidance. Use when building or running tests against a real TIA Portal installation, including firewall and runner setup, or when Openness code runs much slower inside NUnit/test runners than in a console app; not for headless WPF tests.
metadata:
  siemens-depends-on: "openness-base, session-and-project, licensing-and-firewall"
---

# Openness Testing

## Overview

Use this skill for **live** TIA Portal Openness integration tests and their CI environment. It is not guidance for headless WPF tests. Keep live tests opt-in and separate from fast unit tests.

## Live-test project and assembly bootstrap

- Use a separate **`net48`** integration-test project. Do not combine it with a fast modern-.NET unit-test project.
- Reference installed Siemens assemblies with `Private=False`; copying them locally can break Openness install-relative resolution.
- Register `AppDomain.CurrentDomain.AssemblyResolve` early in a method containing **zero** `Siemens.Engineering` type references.
- Call Siemens-referencing code only from a separate `[MethodImpl(MethodImplOptions.NoInlining)]` method, so the resolver is registered before that code is JIT-compiled.

```csharp
[Fact]
public void Live_test()
{
    RegisterOpennessResolver(); // This method has no Siemens.Engineering references.
    RunLiveTest();
}

[MethodImpl(MethodImplOptions.NoInlining)]
private static void RunLiveTest()
{
    using var tia = new TiaPortal(TiaPortalMode.WithoutUserInterface);
    // Code that references Siemens.Engineering types belongs here.
}
```

## Test lifecycle and session safety

- Use the raw Openness API with `TiaPortalMode.WithoutUserInterface`.
- Prefer a portal instance and scratch project owned by the test. Create scratch projects under a unique temporary directory and delete them in `finally` so reruns do not collide with stale project folders.
- If a test attaches to an existing portal, respect independent project and portal ownership: never close or dispose user-owned resources.
- Run live tests explicitly/opt-in; creating and compiling a real project is slow and requires a real installation.
- Build before launching live clients. Do not rebuild shared output assemblies while another Openness process is using them; file locks can make otherwise valid builds fail.
- **Process cleanliness:** to prove a live test leaves no processes behind:
  - Snapshot the existing process identities (PID plus start time) first.
  - Poll `Win32_Process` for new TIA/FileStorage descendants.
  - Terminate only identity-matched descendants that the test owns.

  `Win32_ProcessStartTrace` is not usable here: `ManagementEventWatcher.Start()` fails with `Access denied` in a non-elevated test host.

## Fast-test discovery guard

A test runner can exit successfully with **zero** tests. If a test assembly declares helper or fake classes whose member signatures use `Siemens.Engineering` types (`Project`, `TiaPortal`, `Device` …), discovery calls `GetTypes()` before the Openness resolver is registered. It silently finds no tests in the whole assembly.

- Keep pure unit tests on plain CLR types, without Openness types in signatures.
- Isolate real Siemens interface implementations in the separate opt-in live project.
- Make CI assert that the executed test count is greater than 0.

## Firewall-dialog automation boundaries

The interactive Openness firewall dialog is native, and UI Automation does not reliably expose the needed controls. Raw Win32 automation is permissible only for **trusted, developer-approved test binaries**.

- Confirm only the per-run **Yes** action. Never use **Yes to all** without explicit approval.
- Multi-monitor coordinates can be negative; raw cursor APIs must preserve those coordinates.
- This convenience automation is not a substitute for a permanent administrator allow for unattended production deployments.

## CI prerequisites

Use a dedicated Windows runner with:

- a matching TIA Portal **V21+** installation;
- all required TIA product and option licenses;
- Windows membership in the **Siemens TIA Openness** group; and
- the necessary Openness firewall configuration for the test binary.

Do not imply that generic hosted runners can execute these tests.

## Test-runner overhead on Openness calls (NUnit on net48)

Openness talks to TIA Portal via .NET Remoting, which sends all `ILogicalThreadAffinative` data in the logical `CallContext` with **every** call. NUnit 3 on .NET Framework keeps its `TestExecutionContext` there: a `MarshalByRefObject` in slot `"NUnit.Framework.TestExecutionContext"`. Measured effect: Openness-heavy code ran 3–5× slower inside an NUnit test than in a console app with identical code, settings and DLLs. Pure in-memory code was equally fast in both.

Ruled out as causes: runner (testhost or NUnitLite), AppDomain isolation, TEMP location, visible UI, power plan, GC mode, thread apartment and AppContext switches. A plain exe started as a child of testhost was fast. Only removing the context fixed it.

Fix in test code (no product change):

- Around the Openness-heavy section, save `CallContext.GetData(slot)`, call `CallContext.FreeNamedDataSlot(slot)`, and replace `Console.Out`/`Console.Error` with a synchronized buffer. In `Dispose`, restore both and replay the buffer.
- Both parts are required. NUnit's console-capture writer and every `TestContext` access re-create the context.
- Callbacks running inside the section (event handlers, progress reporters) must access `TestContext` only **after** their Openness calls, or strip the slot again afterwards.
- To diagnose, compare the same code in a plain exe and inside a test. If call counts are identical and only Openness-calling code is slower, suspect per-call marshalling overhead.
- Any in-process host that puts `ILogicalThreadAffinative`/`MarshalByRefObject` data into the logical call context is likely affected. Verify per framework.

## Checklist

- [ ] Separate opt-in `net48` live-test project uses installed assemblies with `Private=False`.
- [ ] Resolver bootstrap has no Siemens types; a separate `NoInlining` method performs live calls.
- [ ] Test uses a test-owned portal and scratch project, with `finally` cleanup.
- [ ] Any attachment leaves user-owned projects and portals open.
- [ ] Firewall automation is limited to developer-approved binaries and per-run **Yes**.
- [ ] CI runner has matching TIA V21+, required licenses, group membership, and firewall setup.
- [ ] CI asserts a non-zero executed test count.
- [ ] NUnit (net48) tests run Openness-heavy code with NUnit's `CallContext` slot removed and console capture redirected.

## Related Files

- [`openness-base`](../openness-base/SKILL.md) — shared SDK and assembly prerequisites
- [`session-and-project`](../session-and-project/SKILL.md) — session lifecycle and independent ownership teardown
- [`licensing-and-firewall`](../licensing-and-firewall/SKILL.md) — product licenses and core firewall policy
