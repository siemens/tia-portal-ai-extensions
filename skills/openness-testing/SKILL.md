---
name: openness-testing
description: Live TIA Portal Openness integration-test and CI guidance. Use when building or running tests against a real TIA Portal installation, including firewall and runner setup; not for headless WPF tests.
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

## Checklist

- [ ] Separate opt-in `net48` live-test project uses installed assemblies with `Private=False`.
- [ ] Resolver bootstrap has no Siemens types; a separate `NoInlining` method performs live calls.
- [ ] Test uses a test-owned portal and scratch project, with `finally` cleanup.
- [ ] Any attachment leaves user-owned projects and portals open.
- [ ] Firewall automation is limited to developer-approved binaries and per-run **Yes**.
- [ ] CI runner has matching TIA V21+, required licenses, group membership, and firewall setup.

## Related Files

- [`openness-base`](../openness-base/SKILL.md) — shared SDK and assembly prerequisites
- [`session-and-project`](../session-and-project/SKILL.md) — session lifecycle and independent ownership teardown
- [`licensing-and-firewall`](../licensing-and-firewall/SKILL.md) — product licenses and core firewall policy
