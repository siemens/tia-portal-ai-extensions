#!/usr/bin/env python3
"""Validate plugin packages, Agent Skills, and their marketplace catalog."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLUGIN_NAME_RE = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
SEMVER_RE = re.compile(
    r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
LINK_RE = re.compile(r"(?<!!)\[[^\]]*]\(([^)]+)\)")
RESOURCE_RE = re.compile(r"`((?:references|assets)/[^`\n]+)`")
PORTABLE_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
EXPECTED_PLUGIN_NAME = "tia-portal-openness-development-kit"
EXPECTED_PLUGIN_VERSION = "1.0.0"
EXPECTED_MARKETPLACE_NAME = "tia-portal-ai-extensions"
DEPENDENCY_METADATA_KEY = "siemens-depends-on"
ALLOWED_SKILL_FIELDS = frozenset(
    {
        "name",
        "description",
        "license",
        "compatibility",
        "metadata",
        "allowed-tools",
    }
)
EXPECTED_SKILLS = frozenset(
    {
        "blocks",
        "change-detection",
        "crash-diagnosis",
        "devices-and-hardware",
        "drive-control-charts",
        "drive-objects",
        "engineering-objects",
        "global-library",
        "hardware-and-modules",
        "libraries-and-alarms",
        "licensing-and-firewall",
        "networks-and-drivecliq",
        "object-tree-walking",
        "online-and-download",
        "openness-base",
        "openness-overview",
        "openness-testing",
        "parameters",
        "performance-and-caching",
        "plc-data-types",
        "plc-safety-administration",
        "safety-commissioning",
        "security",
        "session-and-project",
        "simatic-sd",
        "software-hierarchy",
        "sw-units",
        "tags-and-tagtables",
        "technology-objects",
        "telegrams",
        "threading-and-concurrency",
        "tia-addin-scaffold",
    }
)
EXPECTED_PLUGIN_IDENTITIES = {
    "openness_development": (EXPECTED_PLUGIN_NAME, EXPECTED_PLUGIN_VERSION),
}
EXPECTED_SKILLS_BY_PLUGIN = {
    "openness_development": EXPECTED_SKILLS,
}
PORTABLE_MANIFEST_FIELDS = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}


def load_json(path: Path, errors: list[str]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(ROOT)}: top-level JSON must be an object")
        return None
    return value


def discover_plugin_directories() -> list[Path]:
    if not ROOT.is_dir():
        return []
    return sorted(
        (
            path
            for path in ROOT.iterdir()
            if path.is_dir()
            and ((path / "plugin.json").is_file() or (path / "skills").is_dir())
        ),
        key=lambda path: path.name,
    )


FrontmatterValue = str | dict[str, str]


def parse_frontmatter(
    path: Path, errors: list[str]
) -> tuple[dict[str, FrontmatterValue], str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: cannot read UTF-8: {exc}")
        return {}, ""

    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append(f"{path.relative_to(ROOT)}: missing opening frontmatter")
        return {}, text
    try:
        end = lines.index("---", 1)
    except ValueError:
        errors.append(f"{path.relative_to(ROOT)}: missing closing frontmatter")
        return {}, text

    frontmatter: dict[str, FrontmatterValue] = {}
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line[:1].isspace() or ":" not in line:
            errors.append(
                f"{path.relative_to(ROOT)}:{index + 1}: invalid frontmatter line"
            )
            index += 1
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if key == "metadata" and not raw_value:
            metadata: dict[str, str] = {}
            index += 1
            while index < end:
                nested_line = lines[index]
                if not nested_line.strip():
                    index += 1
                    continue
                if not nested_line[:1].isspace():
                    break
                nested_value = nested_line.strip()
                if ":" not in nested_value or not nested_value.split(":", 1)[0]:
                    errors.append(
                        f"{path.relative_to(ROOT)}:{index + 1}: invalid metadata entry"
                    )
                    index += 1
                    continue
                nested_key, nested_raw_value = nested_value.split(":", 1)
                nested_key = nested_key.strip()
                nested_raw_value = nested_raw_value.strip()
                if (
                    len(nested_raw_value) >= 2
                    and nested_raw_value[0] == nested_raw_value[-1]
                    and nested_raw_value[0] in {'"', "'"}
                ):
                    nested_raw_value = nested_raw_value[1:-1]
                if nested_key in metadata:
                    errors.append(
                        f"{path.relative_to(ROOT)}:{index + 1}: "
                        f"duplicate metadata key {nested_key!r}"
                    )
                else:
                    metadata[nested_key] = nested_raw_value
                index += 1
            frontmatter[key] = metadata
            continue
        if raw_value in {">", ">-", "|", "|-"}:
            continuation: list[str] = []
            index += 1
            while index < end and (
                not lines[index].strip() or lines[index][:1].isspace()
            ):
                continuation.append(lines[index].strip())
                index += 1
            separator = " " if raw_value.startswith(">") else "\n"
            value = separator.join(part for part in continuation if part)
        else:
            value = raw_value
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            index += 1
        frontmatter[key] = value

    return frontmatter, text


def validate_links(path: Path, text: str, errors: list[str]) -> None:
    prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    prose = re.sub(r"`[^`\n]*`", "", prose)
    for match in LINK_RE.finditer(prose):
        raw_target = match.group(1).strip()
        target = raw_target.split(maxsplit=1)[0].strip("<>")
        if (
            not target
            or target == "url"
            or re.match(r"^(?:https?://|mailto:|#)", target)
        ):
            continue
        target = unquote(target.split("#", 1)[0])
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            errors.append(
                f"{path.relative_to(ROOT)}: relative link leaves repository: "
                f"{raw_target}"
            )
            continue
        if not resolved.exists():
            errors.append(
                f"{path.relative_to(ROOT)}: broken relative link: {raw_target}"
            )


def validate_resources(path: Path, text: str, errors: list[str]) -> None:
    prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    for match in RESOURCE_RE.finditer(prose):
        raw_target = match.group(1)
        matches = list(path.parent.glob(raw_target))
        if not matches:
            errors.append(
                f"{path.relative_to(ROOT)}: missing bundled resource: {raw_target}"
            )
            continue
        for resource in matches:
            try:
                resource.resolve().relative_to(ROOT)
            except ValueError:
                errors.append(
                    f"{path.relative_to(ROOT)}: bundled resource leaves "
                    f"repository: {raw_target}"
                )


def validate_dependency_cycles(graph: dict[str, set[str]], errors: list[str]) -> None:
    state: dict[str, int] = {}
    stack: list[str] = []
    reported: set[tuple[str, ...]] = set()

    def visit(name: str) -> None:
        state[name] = 1
        stack.append(name)
        for dependency in sorted(graph.get(name, set())):
            if dependency not in graph:
                continue
            if state.get(dependency, 0) == 0:
                visit(dependency)
            elif state.get(dependency) == 1:
                start = stack.index(dependency)
                cycle = tuple(stack[start:] + [dependency])
                if cycle not in reported:
                    reported.add(cycle)
                    errors.append("dependency cycle: " + " -> ".join(cycle))
        stack.pop()
        state[name] = 2

    for name in sorted(graph):
        if state.get(name, 0) == 0:
            visit(name)


def validate_skills(
    errors: list[str],
    warnings: list[str],
    expected_skills_by_plugin: dict[str, frozenset[str]] | None = (
        EXPECTED_SKILLS_BY_PLUGIN
    ),
) -> None:
    plugin_directories = discover_plugin_directories()
    if not plugin_directories:
        errors.append("no plugin package directories found")
        print("Checked 0 Agent Skills.")
        return

    all_names: dict[str, Path] = {}
    skill_count = 0

    for plugin_directory in plugin_directories:
        skill_paths = sorted((plugin_directory / "skills").glob("*/SKILL.md"))
        skill_count += len(skill_paths)
        if not skill_paths:
            errors.append(
                f"no Agent Skills found under "
                f"{plugin_directory.relative_to(ROOT)}/skills/*/SKILL.md"
            )

        names: dict[str, Path] = {}
        graph: dict[str, set[str]] = {}

        for path in skill_paths:
            frontmatter, text = parse_frontmatter(path, errors)
            relative = path.relative_to(ROOT)
            name_value = frontmatter.get("name", "")
            description_value = frontmatter.get("description", "")
            compatibility_value = frontmatter.get("compatibility", "")
            metadata_value = frontmatter.get("metadata", {})
            name = name_value if isinstance(name_value, str) else ""
            description = description_value if isinstance(description_value, str) else ""
            compatibility = (
                compatibility_value if isinstance(compatibility_value, str) else ""
            )
            metadata = metadata_value if isinstance(metadata_value, dict) else {}

            unknown_fields = sorted(set(frontmatter) - ALLOWED_SKILL_FIELDS)
            if unknown_fields:
                errors.append(
                    f"{relative}: unsupported skill frontmatter fields: "
                    f"{', '.join(unknown_fields)}"
                )
            if "metadata" in frontmatter and not isinstance(metadata_value, dict):
                errors.append(f"{relative}: metadata must be a mapping")

            if not NAME_RE.fullmatch(name) or len(name) > 64:
                errors.append(f"{relative}: invalid or missing skill name: {name!r}")
            elif name != path.parent.name:
                errors.append(
                    f"{relative}: name {name!r} does not match directory "
                    f"{path.parent.name!r}"
                )
            elif name in names:
                errors.append(
                    f"{relative}: duplicate skill name also used by "
                    f"{names[name].relative_to(ROOT)}"
                )
            elif name in all_names:
                errors.append(
                    f"{relative}: duplicate skill name across plugins also used by "
                    f"{all_names[name].relative_to(ROOT)}"
                )
                names[name] = path
            else:
                names[name] = path
                all_names[name] = path

            if not description or len(description) > 1024:
                errors.append(f"{relative}: description must contain 1-1024 characters")
            if compatibility and len(compatibility) > 500:
                errors.append(f"{relative}: compatibility exceeds 500 characters")
            if len(text.splitlines()) > 500:
                warnings.append(f"{relative}: SKILL.md exceeds the recommended 500 lines")

            raw_dependencies = metadata.get(DEPENDENCY_METADATA_KEY, "")
            graph.setdefault(name, set())
            for dependency in raw_dependencies.split(","):
                dependency = dependency.strip()
                if dependency:
                    graph[name].add(dependency)

            validate_resources(path, text, errors)

        for name, dependencies in sorted(graph.items()):
            for dependency in sorted(dependencies):
                if dependency not in names:
                    source_path = names.get(
                        name,
                        plugin_directory / "skills" / name / "SKILL.md",
                    )
                    errors.append(
                        f"{source_path.relative_to(ROOT)}: "
                        f"unknown dependency {dependency!r}"
                    )

        validate_dependency_cycles(graph, errors)

        if expected_skills_by_plugin is not None:
            expected_skills = expected_skills_by_plugin.get(plugin_directory.name)
            if expected_skills is not None:
                discovered = set(names)
                for missing in sorted(expected_skills - discovered):
                    errors.append(
                        f"missing approved skill in {plugin_directory.name}: {missing}"
                    )
                for unexpected in sorted(discovered - expected_skills):
                    errors.append(
                        f"unexpected skill outside approved list in "
                        f"{plugin_directory.name}: {unexpected}"
                    )

    print(
        f"Checked {skill_count} Agent Skills across "
        f"{len(plugin_directories)} plugin package(s)."
    )


def validate_portable_manifest(
    manifest_path: Path, plugin_directory: Path, errors: list[str]
) -> dict | None:
    relative = manifest_path.relative_to(ROOT)
    if not manifest_path.is_file():
        errors.append(f"missing Agent Plugins manifest: {relative}")
        return None

    manifest = load_json(manifest_path, errors)
    if manifest is None:
        return None

    unknown_fields = sorted(set(manifest) - PORTABLE_MANIFEST_FIELDS)
    if unknown_fields:
        errors.append(
            f"{relative}: unsupported top-level fields: {', '.join(unknown_fields)}"
        )
    if manifest.get("$schema") != PORTABLE_SCHEMA:
        errors.append(f"{relative}: missing canonical Agent Plugins 1.0 schema")

    name = manifest.get("name")
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 64
        or not PLUGIN_NAME_RE.fullmatch(name)
    ):
        errors.append(f"{relative}: invalid plugin name: {name!r}")
    if isinstance(name, str) and name in {
        identity[0] for identity in EXPECTED_PLUGIN_IDENTITIES.values()
    } and plugin_directory.name not in EXPECTED_PLUGIN_IDENTITIES:
        errors.append(f"{relative}: plugin name is already used by another package")

    expected_identity = EXPECTED_PLUGIN_IDENTITIES.get(plugin_directory.name)
    if expected_identity is not None:
        expected_name, expected_version = expected_identity
        if name != expected_name:
            errors.append(
                f"{relative}: expected plugin name {expected_name!r}, found {name!r}"
            )

    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        errors.append(f"{relative}: version must be three-part SemVer")
    elif expected_identity is not None and version != expected_identity[1]:
        errors.append(
            f"{relative}: expected version {expected_identity[1]!r}, found {version!r}"
        )

    description = manifest.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{relative}: description must be a non-empty string")

    author = manifest.get("author")
    if author is not None:
        if not isinstance(author, dict):
            errors.append(f"{relative}: author must be an object")
        else:
            unknown_author_fields = sorted(set(author) - {"name", "email", "url"})
            if unknown_author_fields:
                errors.append(
                    f"{relative}: unsupported author fields: "
                    f"{', '.join(unknown_author_fields)}"
                )
            for field, value in author.items():
                if not isinstance(value, str):
                    errors.append(f"{relative}: author.{field} must be a string")

    keywords = manifest.get("keywords")
    if keywords is not None and (
        not isinstance(keywords, list)
        or any(not isinstance(keyword, str) for keyword in keywords)
    ):
        errors.append(f"{relative}: keywords must be an array of strings")

    return manifest


def resolve_plugin_source(
    source: object, marketplace_relative: Path, errors: list[str]
) -> Path | None:
    if not isinstance(source, str) or not source.strip() or "\\" in source:
        errors.append(
            f"{marketplace_relative}: plugin source must be a relative POSIX path"
        )
        return None

    source_path = PurePosixPath(source)
    if (
        source_path.is_absolute()
        or not source_path.parts
        or any(part == ".." for part in source_path.parts)
    ):
        errors.append(
            f"{marketplace_relative}: plugin source must identify a package "
            "inside the repository"
        )
        return None

    resolved = (ROOT / Path(*source_path.parts)).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        errors.append(
            f"{marketplace_relative}: plugin source leaves the repository"
        )
        return None
    return resolved


def validate_manifests(errors: list[str]) -> None:
    plugin_directories = discover_plugin_directories()
    plugin_manifests: dict[Path, dict | None] = {}

    for plugin_directory in plugin_directories:
        portable_path = plugin_directory / "plugin.json"
        portable_manifest = validate_portable_manifest(
            portable_path, plugin_directory, errors
        )
        plugin_manifests[plugin_directory.resolve()] = portable_manifest

    marketplace_path = ROOT / ".github" / "plugin" / "marketplace.json"
    if not marketplace_path.is_file():
        errors.append(
            "missing Copilot marketplace manifest: .github/plugin/marketplace.json"
        )
        print(
            f"Checked {len(plugin_directories)} plugin package(s) and "
            "0 marketplace manifests."
        )
        return

    marketplace = load_json(marketplace_path, errors)
    if marketplace is None:
        print(
            f"Checked {len(plugin_directories)} plugin package(s) and "
            "1 marketplace manifest."
        )
        return

    marketplace_relative = marketplace_path.relative_to(ROOT)
    if marketplace.get("name") != EXPECTED_MARKETPLACE_NAME:
        errors.append(
            f"{marketplace_relative}: expected marketplace name "
            f"{EXPECTED_MARKETPLACE_NAME!r}"
        )
    owner = marketplace.get("owner")
    if (
        not isinstance(owner, dict)
        or not isinstance(owner.get("name"), str)
        or not owner["name"].strip()
    ):
        errors.append(f"{marketplace_relative}: owner.name must be a non-empty string")

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        errors.append(f"{marketplace_relative}: plugins must be a non-empty array")
        plugins = []

    package_directories = set(plugin_manifests)
    entries_by_source: dict[Path, dict] = {}
    entry_names: set[str] = set()
    entry_sources: set[Path] = set()

    for index, plugin in enumerate(plugins):
        entry_context = f"{marketplace_relative}: plugins[{index}]"
        if not isinstance(plugin, dict):
            errors.append(f"{entry_context}: entry must be an object")
            continue

        name = plugin.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{entry_context}: name must be a non-empty string")
        elif name in entry_names:
            errors.append(f"{entry_context}: duplicate plugin name {name!r}")
        else:
            entry_names.add(name)

        source = resolve_plugin_source(plugin.get("source"), marketplace_relative, errors)
        if source is None:
            continue
        if source in entry_sources:
            errors.append(f"{entry_context}: duplicate plugin source {plugin['source']!r}")
            continue
        entry_sources.add(source)
        if source not in package_directories:
            errors.append(
                f"{entry_context}: source {plugin['source']!r} does not identify "
                "a plugin package"
            )
            continue
        entries_by_source[source] = plugin

        manifest = plugin_manifests.get(source)
        if manifest is None:
            continue
        if name != manifest.get("name"):
            errors.append(
                f"{entry_context}: plugin name differs from its plugin.json"
            )
        for field in ("description", "version", "author", "license", "keywords"):
            if plugin.get(field) != manifest.get(field):
                errors.append(
                    f"{entry_context}: plugin {field} differs from plugin.json"
                )

    for plugin_directory in plugin_directories:
        resolved_directory = plugin_directory.resolve()
        if resolved_directory not in entries_by_source:
            errors.append(
                f"{marketplace_relative}: missing marketplace entry for "
                f"{plugin_directory.relative_to(ROOT)}"
            )

    print(
        f"Checked {len(plugin_directories)} plugin package(s) and "
        "1 marketplace manifest."
    )


def validate_documents(errors: list[str]) -> None:
    markdown_paths = sorted(ROOT.rglob("*.md"))
    for path in markdown_paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: cannot read UTF-8: {exc}")
            continue
        validate_links(path, text, errors)

    print(f"Checked {len(markdown_paths)} Markdown documents.")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    validate_skills(errors, warnings)
    validate_manifests(errors)
    validate_documents(errors)

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    if errors:
        print(f"FAILED: {len(errors)} validation error(s):", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print("OK: Agent Skills, documents, and plugin manifests are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
