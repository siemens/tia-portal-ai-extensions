---
name: licensing-and-firewall
description: Openness application-level licensing and access control (the Openness firewall). Use when an app is denied access to TIA Portal, when a LicenseNotFoundException occurs, or when explaining what rights/licenses an Openness app needs. Distinct from the security skill, which covers project-internal UMAC roles.
metadata:
  siemens-depends-on: "openness-base"
---

# Licensing and Firewall

## Overview

This skill covers **application-level** access control for Openness itself — whether an app is allowed to run against TIA Portal at all, and which product licenses it needs. This is a different layer from the `security` skill, which covers **project-internal** UMAC roles, device function rights, and PLC master passwords.

## Common Patterns

### Licensing — No Separate Openness License

**Description:** There is no dedicated Openness license. An Openness app needs the same licenses as the products/options it drives (e.g. STEP 7 Professional, STEP 7 Safety). If a required license is missing, TIA Portal throws `LicenseNotFoundException`.

**Key points:**
- Check which product/option a given API call requires and ensure that license is available in the environment before relying on the call.
- Surface `LicenseNotFoundException` to the user with the specific missing product/option rather than a generic failure message.

### The Openness Firewall — App-Level Access Control

**Description:** Beyond project-internal security (UMAC), TIA Portal has an **Openness firewall** that controls whether a given application is allowed to connect to a running TIA Portal instance at all.

**How it works:**
- **Group membership gate:** Administrators grant users the right to run Openness apps at all via local Windows group membership in **"Siemens TIA Openness"**. Without this membership, no Openness app can attach to TIA Portal for that user.
- **Interactive per-app allow/deny:** When an unrecognized app tries to connect, the interactive user is prompted to temporarily allow or deny that specific app's access to the active TIA Portal instance.
- **Permanent allow via administrator:** Administrators can permanently allow an app to access every TIA Portal instance, configured via the firewall plus Windows registry entries — useful for unattended/service scenarios where no interactive user is present to click "allow".
- **Code-signing bypass:** Siemens applications signed with a special Openness code-signing certificate automatically pass the Openness firewall without a prompt.

**Key points:**
- If your app is meant to run unattended (service, scheduled task, MCP-style server), plan for the **permanent allow** configuration up front — an interactive allow/deny prompt will otherwise block headless execution.
- Denial surfaces as `EngineeringSecurityException` — handle it and guide the user to the firewall setting rather than crashing or retrying blindly.

## Quick Reference

| Concept | Purpose |
|---|---|
| No dedicated Openness license | Openness itself needs no license; underlying products/options do |
| `LicenseNotFoundException` | Thrown when a required product/option license is missing |
| "Siemens TIA Openness" Windows group | Gates whether a user may run Openness apps at all |
| Interactive per-app allow/deny | Temporary firewall decision made by the logged-in user |
| Permanent allow (admin + registry) | Required for unattended/headless Openness apps |
| Openness code-signing certificate | Lets Siemens-signed apps bypass the firewall prompt |
| `EngineeringSecurityException` | Thrown when the firewall denies app access |

## Related Files

- [`security`](../security/SKILL.md) — project-internal UMAC roles, device function rights, and PLC master password (a different, project-level security layer)
- [`engineering-objects`](../engineering-objects/SKILL.md) — general exception-handling patterns for Openness apps
- [`session-and-project`](../session-and-project/SKILL.md) — creating/attaching `TiaPortal` instances, where firewall checks occur
- [`openness-testing`](../openness-testing/SKILL.md) — live-test firewall-dialog automation boundaries and CI prerequisites

## Exception Handling

- `LicenseNotFoundException` — a required product/option license is missing; surface the specific missing license to the user.
- `EngineeringSecurityException` — the Openness firewall denied the app; guide the user to allow the app (interactively) or have an administrator permanently allow it via the registry.
- You can only reach TIA Portal processes running under the **same Windows user** as your app — attempts to reach a different user's TIA Portal instance will fail regardless of firewall configuration.
