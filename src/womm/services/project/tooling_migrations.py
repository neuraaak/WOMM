"""Apply only reviewed, version-scoped configuration transformations."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from womm.exceptions.project import ProjectServiceError

from .config_document import ConfigDocument
from .tooling_environment import ToolingEnvironment


def require_destructive(allowed: bool, description: str) -> None:
    """An unsafe flag authorizes known operations, never ambiguous values."""
    if not allowed:
        raise ProjectServiceError(
            "tooling_migration",
            f"{description}: requires --allow-destructive-actions; no project files or installed tools were changed",
        )


def check_transition(
    registry: dict[str, Any], tool: str, source: str, target: str, allowed: bool
) -> list[dict[str, Any]]:
    """Same-minor patches are supported; crossing another boundary needs a rule."""
    before, after = Version(source), Version(target)
    transitions = [
        rule
        for rule in registry["transitions"]
        if rule["tool"] == tool
        and before in SpecifierSet(rule["source"])
        and after in SpecifierSet(rule["target"])
    ]
    if before.release[:2] != after.release[:2] and not transitions:
        raise ProjectServiceError(
            "tooling_migration",
            f"{tool}: no reviewed migration covers {source} to {target}; manual review is required, even with --allow-destructive-actions",
        )
    for rule in transitions:
        if rule.get("destructive"):
            require_destructive(allowed, f"{tool}: {rule['id']}")
    return transitions


def apply_moves(
    document: ConfigDocument,
    prefix: list[str],
    rule: dict[str, Any],
    allowed: bool,
) -> list[str]:
    """Preserve a scalar exactly; collections need explicit structural consent."""
    changes = []
    if rule["operation"] != "move":
        raise ProjectServiceError(
            "tooling_migration",
            "An unsupported registry operation requires manual review",
        )
    for key in rule["keys"]:
        source = [*prefix, *rule["source_prefix"], key]
        destination = [*prefix, *rule["destination_prefix"], key]
        if not document.has(source):
            continue
        value = document.get(source)
        if document.has(destination) and document.get(destination) != value:
            raise ProjectServiceError(
                "tooling_migration",
                f"Conflicting configuration keys: {'.'.join(source)} and {'.'.join(destination)}; manual resolution is required",
            )
        if isinstance(value, (Mapping, list)) or rule.get("destructive"):
            require_destructive(allowed, f"Move configuration block {'.'.join(source)}")
        if document.has(destination):
            document.remove(source)
        else:
            document.move(source, destination)
        changes.append(f"{rule['id']}: {'.'.join(source)} -> {'.'.join(destination)}")
    return changes


def migrate(
    project: Path,
    registry: dict[str, Any],
    environment: ToolingEnvironment,
    source: dict[str, str],
    target: dict[str, str],
    constraints: dict[str, str],
    allowed: bool,
) -> list[str]:
    """Mutate the staged copy only, after checking all required permissions."""
    changes: list[str] = []
    for tool, version in target.items():
        if Version(version) < Version(source[tool]):
            raise ProjectServiceError(
                "tooling_migration",
                f"{tool}: refusing to downgrade from {source[tool]} to {version}",
            )
        transitions = check_transition(registry, tool, source[tool], version, allowed)
        for rule in transitions:
            if rule["operation"] != "biome-migrate" or tool != "@biomejs/biome":
                raise ProjectServiceError(
                    "tooling_migration",
                    "An unsupported transition requires manual review",
                )
            environment.tool(project, "biome", ["migrate", "--write"])
            changes.append(rule["id"])

    if "ruff" in target:
        candidates = []
        for filename in ("ruff.toml", ".ruff.toml"):
            if (project / filename).is_file():
                candidates.append((project / filename, []))
        pyproject = ConfigDocument(project / "pyproject.toml")
        if pyproject.has(["tool", "ruff"]):
            candidates.append((project / "pyproject.toml", ["tool", "ruff"]))
        if len(candidates) > 1:
            raise ProjectServiceError(
                "tooling_migration",
                "Multiple Ruff configuration files require manual review",
            )
        for path, prefix in candidates:
            document = ConfigDocument(path)
            for rule in registry["normalizations"]:
                if rule["tool"] == "ruff" and Version(target["ruff"]) in SpecifierSet(
                    rule["target"]
                ):
                    changes.extend(apply_moves(document, prefix, rule, allowed))
            guard = [*prefix, "required-version"]
            if document.has(guard) and document.get(guard) != constraints["ruff"]:
                if Version(source["ruff"]) not in SpecifierSet(
                    str(document.get(guard))
                ):
                    raise ProjectServiceError(
                        "tooling_migration",
                        "The Ruff version guard disagrees with the current tool version; manual review is required",
                    )
                require_destructive(allowed, "Change Ruff's required-version value")
                document.set(guard, constraints["ruff"])
                changes.append("ruff-required-version: align the version guard")
            if document.content() != document.original:
                document.write()

    if "black" in target:
        document = ConfigDocument(project / "pyproject.toml")
        path = ["tool", "black", "required-version"]
        if document.has(path):
            guard = str(document.get(path))
            if guard not in (target["black"], str(Version(target["black"]).major)):
                if guard not in (source["black"], str(Version(source["black"]).major)):
                    raise ProjectServiceError(
                        "tooling_migration",
                        "The Black version guard needs manual review",
                    )
                require_destructive(allowed, "Remove Black's exact version guard")
                document.remove(path)
                document.write()
                changes.append("black-required-version: remove the exact guard")

    if "@biomejs/biome" in target:
        candidates = [
            project / name
            for name in ("biome.json", "biome.jsonc")
            if (project / name).is_file()
        ]
        if len(candidates) > 1:
            raise ProjectServiceError(
                "tooling_migration",
                "Multiple Biome configuration files require manual review",
            )
        for path in candidates:
            document = ConfigDocument(path)
            if document.has(["$schema"]):
                schema = document.get(["$schema"])
                prefix = "https://biomejs.dev/schemas/"
                if (
                    isinstance(schema, str)
                    and schema.startswith(prefix)
                    and schema != f"{prefix}{target['@biomejs/biome']}/schema.json"
                ):
                    require_destructive(
                        allowed, "Change Biome's versioned schema reference"
                    )
                    if environment.manager == "yarn":
                        document.remove(["$schema"])
                    else:
                        document.set(
                            ["$schema"],
                            "./node_modules/@biomejs/biome/configuration_schema.json",
                        )
                    document.write()
                    changes.append("biome-schema: follow the project package layout")
    return changes
