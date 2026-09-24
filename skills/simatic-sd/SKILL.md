---
name: simatic-sd
description: SIMATIC SD block document format (.s7dcl / .s7res), the V21 Openness export/import API, and programmatic network insertion via round-trip export → text-edit → import. Use when writing or reviewing C# code that exports PLC blocks as SD documents, modifies network content, detects programming languages from SD syntax, inserts new networks, or re-imports modified blocks.
metadata:
  siemens-depends-on: "openness-base, blocks"
---

# SIMATIC SD Format & Network Insertion

## Overview

The SIMATIC SD format (`.s7dcl` / `.s7res`) is TIA Portal V21's block document format. It enables programmatic round-trip modification of block networks: export a block to text, insert or edit networks, then re-import. This is the correct path for adding LAD/FBD/SCL networks to existing blocks via Openness.

## Required Namespaces

```csharp
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.SW.ExternalSources;
```

## Required Assemblies

- `Siemens.Engineering.Base.dll`
- `Siemens.Engineering.Step7.dll`

---

## 1. File Structure Overview

Export produces **two files** per block:
- `BlockName.s7dcl` — code: block header, interface sections, networks
- `BlockName.s7res` — language-dependent resource strings (titles, comments)

### Block-level structure (`.s7dcl`)

```
{
	S7_Optimized := "TRUE";
	S7_PreferredLanguage := "LAD";    ← block's default language
	S7_Version := "0.1"
}
FUNCTION_BLOCK "MyFB"
	VAR_INPUT
		Input1 : Bool;
	END_VAR

	{ S7_Language := "LAD" }          ← per-network language pragma (immediately before NETWORK)
	NETWORK
		RUNG wire#powerrail
			Contact( #Input1 )
			Coil( #Output1 )
		END_RUNG
	END_NETWORK

END_FUNCTION_BLOCK
```

### Block declaration keywords

| Block type | Open keyword | Close keyword |
|---|---|---|
| Function Block | `FUNCTION_BLOCK "Name"` | `END_FUNCTION_BLOCK` |
| Function | `FUNCTION "Name" : RetType` | `END_FUNCTION` |
| Organization Block | `ORGANIZATION_BLOCK "Name"` | `END_ORGANIZATION_BLOCK` |
| Global Data Block | `DATA_BLOCK "Name"` | `END_DATA_BLOCK` |

**Key structural rules:**
- The `{ S7_Language := "LAD" }` pragma sits on the line **immediately before** its `NETWORK` keyword — they must always stay together.
- `S7_PreferredLanguage` in the file header is the block-level fallback; each network carries its own pragma.
- The `.s7res` file must be in the same directory as the `.s7dcl` for import to succeed.

---

## 2. Export API (V21)

```csharp
// Delete existing files first — ExportAsDocuments throws if they already exist
var s7dclFile = Path.Combine(exportDir, block.Name + ".s7dcl");
var s7resFile = Path.Combine(exportDir, block.Name + ".s7res");
if (File.Exists(s7dclFile)) File.Delete(s7dclFile);
if (File.Exists(s7resFile)) File.Delete(s7resFile);

block.ExportAsDocuments(new DirectoryInfo(exportDir), block.Name);
// → produces BlockName.s7dcl + BlockName.s7res
```

**ANTI-PATTERN:** Do NOT use `block.Export(FileInfo, ExportOptions)` for SD — that is XML export.

---

## 3. Import API (V21)

```csharp
// Use PlcBlockComposition.ImportFromDocuments (NOT ExternalSources)
var dir  = new DirectoryInfo(Path.GetDirectoryName(s7dclFilePath));
var name = Path.GetFileNameWithoutExtension(s7dclFilePath);

DocumentImportResultForBlocks result = targetBlockGroup.Blocks.ImportFromDocuments(
	dir,
	name,
	ImportDocumentOptions.Override);

if (result.State == DocumentResultState.Failure)
{
	var messages = string.Join("\n", result.Messages.Select(m => m.Message));
	throw new InvalidOperationException($"SD import failed:\n{messages}");
}
```

**ANTI-PATTERN:** Do NOT use `ExternalSources.CreateFromFile` + `GenerateBlocksFromSource` for `.s7dcl` files — that path treats the file as raw SCL text and produces wrong results.

### Common failure messages

| Message | Root cause |
|---|---|
| `Syntax Error: Unexpected input '{ S7_Language := "..." }'` | Duplicate pragma — preceding network's pragma was not included in `StartLine`, so a new network was inserted between an existing pragma and its `NETWORK` keyword |
| `Syntax Error: expecting END_ORGANIZATION_BLOCK` after `NETWORK` | `NETWORK` block missing its preceding pragma — same duplicate-pragma bug |
| `File Content has some discrepancies` | Structural parse error — missing `END_RUNG`, mismatched RUNG type, or extra blank lines inside RUNG body |

---

## 4. Parsing Networks from `.s7dcl`

```csharp
private static readonly Regex NetworkStartRegex   = new Regex(@"^\s*NETWORK\s*$",   RegexOptions.Compiled);
private static readonly Regex NetworkEndRegex     = new Regex(@"^\s*END_NETWORK\s*$", RegexOptions.Compiled);
private static readonly Regex PragmaLanguageRegex = new Regex(
	@"S7_Language\s*:=\s*""(\w+)""", RegexOptions.Compiled);

public IReadOnlyList<NetworkInfo> ParseNetworksFromLines(string[] lines)
{
	var networks = new List<NetworkInfo>();
	int networkNumber = 0;
	for (int i = 0; i < lines.Length; i++)
	{
		if (!NetworkStartRegex.IsMatch(lines[i])) continue;
		networkNumber++;

		// CRITICAL: StartLine must include the preceding S7_Language pragma line.
		// Inserting at the NETWORK line instead detaches pragma from its NETWORK
		// and causes duplicate-pragma / orphan-NETWORK import failure.
		int startLine = i;
		if (startLine > 0 && PragmaLanguageRegex.IsMatch(lines[startLine - 1]))
			startLine--;

		int endLine = lines.Length - 1;
		for (int j = i + 1; j < lines.Length; j++)
			if (NetworkEndRegex.IsMatch(lines[j])) { endLine = j; break; }

		string lang = null;
		var pm = PragmaLanguageRegex.Match(lines[i - 1 >= 0 ? i - 1 : 0]);
		if (pm.Success) lang = pm.Groups[1].Value;
		if (lang == null) lang = DetectLanguageFromRungs(lines, i + 1, endLine - 1);

		networks.Add(new NetworkInfo
		{
			Number    = networkNumber,
			StartLine = startLine,   // includes pragma line
			EndLine   = endLine,     // END_NETWORK line
			Language  = lang ?? "LAD",
		});
		i = endLine;
	}
	return networks;
}
```

---

## 5. Language Detection from Syntax

```csharp
private static readonly Regex RungLadRegex = new Regex(
	@"^\s*RUNG\s+wire#", RegexOptions.Compiled | RegexOptions.IgnoreCase);
private static readonly Regex RungFbdRegex = new Regex(
	@"^\s*RUNG\s+(\d+|"")", RegexOptions.Compiled | RegexOptions.IgnoreCase);

public string DetectLanguageFromContent(string content)
{
	var lines = content.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None);

	// 1. Explicit S7_Language pragma wins
	foreach (var line in lines)
	{
		var m = PragmaLanguageRegex.Match(line);
		if (m.Success) return m.Groups[1].Value;
	}

	// 2. RUNG wire# → LAD;  RUNG N or RUNG "..." → FBD
	bool hasLad = lines.Any(l => RungLadRegex.IsMatch(l));
	bool hasFbd = lines.Any(l => RungFbdRegex.IsMatch(l));
	if (hasLad && !hasFbd) return "LAD";
	if (hasFbd && !hasLad) return "FBD";

	// 3. No RUNG at all → SCL (plain statements)
	bool hasRung = lines.Any(l => Regex.IsMatch(l, @"^\s*RUNG\b", RegexOptions.IgnoreCase));
	if (!hasRung && lines.Any(l => !string.IsNullOrWhiteSpace(l))) return "SCL";

	return null; // ambiguous — caller must specify explicitly
}
```

| RUNG pattern | Language |
|---|---|
| `RUNG wire#powerrail` or `RUNG wire#wN` | LAD |
| `RUNG 1` or `RUNG "DB.variable"` | FBD |
| No RUNG + has content | SCL |
| Explicit `{ S7_Language := "X" }` | X (overrides all heuristics) |

---

## 6. Normalizing a Raw Code Snippet into an SD Network Block

Input forms accepted:

| Form | Example |
|---|---|
| RUNG body only | `RUNG wire#powerrail\n  Contact(...)\nEND_RUNG` |
| Full `NETWORK...END_NETWORK` | with or without preceding `{ S7_Language }` pragma |
| SCL statement(s) | `#x := #a + #b;` |

```csharp
public string NormalizeNetworkContent(string content, string language)
{
	var inputLines = content.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None);

	// Strip ONLY outer wrappers. Keep inner pragmas like { S7_Templates := "..." }.
	var bodyLines = new List<string>();
	foreach (var line in inputLines)
	{
		var t = line.Trim();
		if (string.IsNullOrWhiteSpace(t)) continue;
		if (PragmaLanguageRegex.IsMatch(t)) continue;           // S7_Language pragma only
		if (Regex.IsMatch(t, @"^NETWORK\s*$",     RegexOptions.IgnoreCase)) continue;
		if (Regex.IsMatch(t, @"^END_NETWORK\s*$", RegexOptions.IgnoreCase)) continue;
		bodyLines.Add(t);
	}

	var sb = new StringBuilder();
	sb.AppendLine($"    {{ S7_Language := \"{language}\" }}");
	sb.AppendLine("    NETWORK");
	foreach (var line in bodyLines)
		sb.AppendLine("        " + line);
	sb.Append("    END_NETWORK");
	return sb.ToString();
}
```

**ANTI-PATTERN:** Do NOT strip ALL `{ ... }` pragma lines with `^\{.*\}$` — this also removes inner `{ S7_Templates := "..." }` pragmas that are valid inside a RUNG and must be preserved.

---

## 7. Inserting a Network at a Specific Position

```csharp
public void InsertNetwork(string s7dclFilePath, string networkContent, int position, string language)
{
	var lines    = File.ReadAllLines(s7dclFilePath).ToList();
	var networks = ParseNetworksFromLines(lines.ToArray());

	var normalized = NormalizeNetworkContent(networkContent, language);
	var newLines   = normalized.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None)
							   .Concat(new[] { "" })   // blank-line separator
							   .ToList();

	int insertIndex;
	if (position <= 0 || networks.Count == 0)
		insertIndex = networks.Count > 0 ? networks[0].StartLine : FindEndBlockLine(lines);
	else if (position > networks.Count)
		insertIndex = networks[networks.Count - 1].EndLine + 1;
	else
		insertIndex = networks[position - 1].StartLine; // before 1-based position

	lines.InsertRange(insertIndex, newLines);
	File.WriteAllLines(s7dclFilePath, lines);
}
```

---

## 8. Full Round-Trip Pattern

```csharp
// 1. Export
var exportDir = Path.Combine(Path.GetTempPath(), "SdExport");
Directory.CreateDirectory(exportDir);
// Delete old files, then export
var s7dclPath = Path.Combine(exportDir, block.Name + ".s7dcl");
var s7resPath = Path.Combine(exportDir, block.Name + ".s7res");
if (File.Exists(s7dclPath)) File.Delete(s7dclPath);
if (File.Exists(s7resPath)) File.Delete(s7resPath);
block.ExportAsDocuments(new DirectoryInfo(exportDir), block.Name);

// 2. Modify — insert networks
foreach (var networkDef in networkDefinitions)
{
	if (string.IsNullOrWhiteSpace(networkDef.Code)) continue;

	var language = networkDef.Language
		?? DetectLanguageFromContent(networkDef.Code)
		?? throw new InvalidOperationException(
			$"Cannot determine language for network '{networkDef.Name}'. Specify explicitly.");

	var existingCount = ParseNetworks(s7dclPath).Count;
	InsertNetwork(s7dclPath, networkDef.Code, existingCount + 1, language);
}

// 3. Re-import
var dir    = new DirectoryInfo(Path.GetDirectoryName(s7dclPath));
var name   = Path.GetFileNameWithoutExtension(s7dclPath);
var result = targetBlockGroup.Blocks.ImportFromDocuments(dir, name, ImportDocumentOptions.Override);
if (result.State == DocumentResultState.Failure)
	throw new InvalidOperationException(string.Join("\n", result.Messages.Select(m => m.Message)));
```

---

## 9. Network Code Input Guidelines

When supplying network code (e.g. from a manifest or data model), use a multi-line string and let language auto-detection run from RUNG syntax. The language must be specified **explicitly for SCL** (no RUNG syntax to detect from).

```text
Network: LadNetwork
  # Language omitted — auto-detected from RUNG wire# → LAD
  Code:
    RUNG wire#powerrail
      Contact( #Input1 )
      { S7_Templates := "time_type := Time" }
      "IEC_Timer_0_DB_1".TON(
          pt := T#1MS,
          et =>
      )
    END_RUNG

Network: SclNetwork
  Language: SCL          # required — SCL has no RUNG to detect from
  Code:
    #Output1 := #Input1 AND #Remanence;
```

**ANTI-PATTERN:** Do NOT wrap the code value in `"..."` quotes — the quotes become literal characters in the string and will appear in the inserted RUNG, causing parse errors on import.

---

## 10. Constraints and Known Limitations

- One network per code entry — each `Code` value must contain exactly one `NETWORK...END_NETWORK` block. Multiple pairs in a single string must be rejected.
- The `.s7res` file is NOT modified during network insertion — resource strings (network titles, comments) are not supported in the code-insertion flow.
- For **SCL** language, auto-detection produces no result (no RUNG syntax). The language must be specified explicitly.
- Mixed LAD/FBD within a single network is ambiguous — detection returns `null` and language must be specified explicitly.

## Quick Reference

| Goal | API / Pattern |
|---|---|
| Export block as SD | `block.ExportAsDocuments(directoryInfo, block.Name)` — delete existing files first |
| Import modified SD | `blockGroup.Blocks.ImportFromDocuments(dir, name, ImportDocumentOptions.Override)` |
| Parse networks from lines | `ParseNetworksFromLines(lines)` — `StartLine` includes preceding pragma |
| Detect language from RUNG | `DetectLanguageFromContent(code)` — see RUNG pattern table |
| Normalize raw snippet | `NormalizeNetworkContent(code, language)` |
| Insert network at position | `InsertNetwork(path, code, position, language)` |

## Common Failure Modes

| Symptom | Root cause | Fix |
|---|---|---|
| `ExportAsDocuments` throws | Previous export files not deleted | Delete `.s7dcl` and `.s7res` before export |
| Duplicate pragma / orphan NETWORK on import | `StartLine` set to NETWORK keyword, not pragma | Set `StartLine` to the preceding pragma line |
| `File Content has some discrepancies` | Inner `{ S7_Templates }` pragma stripped | Strip only `S7_Language` pragma, not all `{ ... }` blocks |
| SD import using wrong API | `ExternalSources.GenerateBlocksFromSource` used | Use `ImportFromDocuments` for `.s7dcl` files |

## Related Files

- [`blocks`](../blocks/SKILL.md) — block import/export (XML path) and compilation
- [`session-and-project`](../session-and-project/SKILL.md) — TIA Portal session lifecycle
