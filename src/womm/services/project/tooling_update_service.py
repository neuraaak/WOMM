"""Plan official tooling updates in isolation before changing a project."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from womm._version import __version__
from womm.exceptions.project import ProjectServiceError
from womm.shared.paths import packaged_assets
from womm.shared.results.update_results import ToolingUpdateResult

from .config_document import ConfigDocument
from .template_store_service import TemplateStoreService
from .tooling_environment import ToolingEnvironment
from .tooling_migrations import check_transition, migrate


def confined(project: Path, name: str) -> Path:
    """Refuse linked files and directories, including dangling links."""
    path = project / name
    for component in (path, *path.parents):
        if component == project:
            break
        if component.is_symlink() or component.is_junction():
            raise ProjectServiceError(
                "tooling_update", f"Linked update path requires manual review: {name}"
            )
    if not path.resolve().is_relative_to(project):
        raise ProjectServiceError("tooling_update", "An update path leaves the project")
    return path


def write_atomic(path: Path, content: bytes) -> None:
    """Replace one file only after its complete replacement is on disk."""
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=".womm-write-", delete=False
    ) as output:
        temporary = Path(output.name)
        output.write(content)
    try:
        if path.exists():
            temporary.chmod(path.stat().st_mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def declarations(
    document: ConfigDocument, language: str
) -> list[tuple[list[str], int | None, str, str]]:
    """Find tools actually declared today, following Python dev include-groups."""
    result = []
    if language == "javascript":
        if document.has(["workspaces"]):
            raise ProjectServiceError(
                "tooling_update", "Workspace updates require manual review"
            )
        for name, value in document.get(["devDependencies"]).items():
            result.append((["devDependencies", name], None, name, value))
        return result
    groups = document.get(["dependency-groups"])
    visited: set[str] = set()

    def visit(group: str, ancestors: set[str]) -> None:
        if group in ancestors:
            raise ProjectServiceError(
                "tooling_update", "Cyclic dependency groups require manual review"
            )
        if group in visited:
            return
        visited.add(group)
        for index, value in enumerate(groups[group]):
            if isinstance(value, str):
                requirement = Requirement(value)
                result.append(
                    (
                        ["dependency-groups", group],
                        index,
                        canonicalize_name(requirement.name),
                        value,
                    )
                )
            elif isinstance(value, dict) and set(value) == {"include-group"}:
                visit(value["include-group"], ancestors | {group})
            else:
                raise ProjectServiceError(
                    "tooling_update", "Unsupported dependency group entry"
                )

    visit("dev", set())
    return result


class ToolingUpdateService:
    """Update dependencies and known configuration keys without regenerating code."""

    def update(
        self,
        project: Path,
        *,
        dry_run: bool = False,
        allow_destructive_actions: bool = False,
        approve: Callable[[ToolingUpdateResult], bool] | None = None,
    ) -> ToolingUpdateResult:
        project = project.resolve()
        provenance_path = confined(project, ".womm-template.json")
        if not provenance_path.is_file():
            raise ProjectServiceError(
                "tooling_update",
                "This update requires an official .womm-template.json provenance file",
            )
        provenance_bytes = provenance_path.read_bytes()
        provenance = json.loads(provenance_bytes)
        if provenance.get("schema_version") != 1 or provenance.get("template") not in (
            "official/python",
            "official/javascript",
        ):
            raise ProjectServiceError(
                "tooling_update",
                "Unsupported template provenance; manual review is required",
            )
        template = TemplateStoreService().resolve(provenance["template"])
        language = template.setup_language
        registry = json.loads(
            packaged_assets().joinpath("migrations", "tooling.json").read_text("utf-8")
        )
        seeds = yaml.safe_load((template.source / "copier.yml").read_text("utf-8"))[
            "tool_versions"
        ]["default"]
        environment = ToolingEnvironment(project, language)
        manifest = ConfigDocument(confined(project, environment.manifest))
        candidates = [
            environment.manifest,
            *environment.lockfiles,
            ".womm-template.json",
            ".womm-update.json",
            "ruff.toml",
            ".ruff.toml",
            "biome.json",
            "biome.jsonc",
        ]
        original = {
            name: path.read_bytes()
            if (path := confined(project, name)).is_file()
            else None
            for name in candidates
        }
        if (
            original[environment.manifest] != manifest.original
            or original[".womm-template.json"] != provenance_bytes
        ):
            raise ProjectServiceError(
                "tooling_update",
                "Project files changed while being read; run the update again",
            )
        entries = [
            entry
            for entry in declarations(manifest, language)
            if entry[2] in registry["tools"]
            and registry["tools"][entry[2]]["version_key"] in seeds
        ]
        names = sorted({entry[2] for entry in entries})
        if not names:
            raise ProjectServiceError(
                "tooling_update", "No managed development tools are declared"
            )
        source = environment.versions(project, names)
        constraints = {}
        for name in names:
            if not source[name]:
                raise ProjectServiceError(
                    "tooling_update",
                    f"{name}: no project-local installed or locked version; synchronize the project first",
                )
            seed = str(seeds[registry["tools"][name]["version_key"]])
            check_transition(
                registry, name, source[name], seed, allow_destructive_actions
            )
            exact = (
                name in ("vitest", "@vitest/coverage-v8")
                and "@vitest/coverage-v8" in names
            )
            constraints[name] = (
                "~=" if language == "python" else "" if exact else "~"
            ) + seed

        # Never follow project links into another checkout, credential store or venv.
        def ignore(directory: str, children: list[str]) -> set[str]:
            excluded = {
                ".git",
                ".venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
                ".womm-backups",
                ".womm-update.lock",
                ".aws",
                ".ssh",
            }
            return {
                name
                for name in children
                if name in excluded
                or name.startswith(".env")
                or (Path(directory) / name).is_symlink()
                or (Path(directory) / name).is_junction()
            }

        with tempfile.TemporaryDirectory(prefix="womm-update-") as temporary:
            stage = Path(temporary) / "project"
            shutil.copytree(project, stage, ignore=ignore)
            staged = ConfigDocument(stage / environment.manifest)
            for path, index, name, value in entries:
                if language == "python":
                    requirement = Requirement(value)
                    if requirement.url or requirement.marker:
                        raise ProjectServiceError(
                            "tooling_update",
                            f"{name}: conditional or URL requirement needs manual review",
                        )
                    extras = (
                        f"[{','.join(sorted(requirement.extras))}]"
                        if requirement.extras
                        else ""
                    )
                    staged.tree[path[0]][path[1]][index] = (
                        f"{requirement.name}{extras}{constraints[name]}"
                    )
                else:
                    if not isinstance(value, str) or value.startswith(
                        ("workspace:", "file:", "git", "http", "npm:")
                    ):
                        raise ProjectServiceError(
                            "tooling_update",
                            f"{name}: non-registry requirement needs manual review",
                        )
                    staged.set(path, constraints[name])
            staged.write()
            expected_manifest = (
                staged.get(["devDependencies"]) if language == "javascript" else None
            )
            target = environment.resolve(stage, names)
            if language == "javascript":
                resolved_manifest = ConfigDocument(stage / environment.manifest)
                if resolved_manifest.get(["devDependencies"]) != expected_manifest:
                    raise ProjectServiceError(
                        "tooling_update",
                        "The package manager rewrote dependency declarations; manual review is required",
                    )
            if any(not target.get(name) for name in names):
                raise ProjectServiceError(
                    "tooling_update",
                    "The target resolver did not report all managed tool versions",
                )
            migrations = migrate(
                stage,
                registry,
                environment,
                source,
                target,
                constraints,
                allow_destructive_actions,
            )
            environment.validate(stage, names, registry["tools"])
            changed = {
                name: (stage / name).read_bytes()
                for name in candidates
                if name not in (".womm-template.json", ".womm-update.json")
                and (stage / name).is_file()
                and (stage / name).read_bytes() != original[name]
            }
            report = ToolingUpdateResult(
                success=True,
                updates=[(name, source[name], target[name]) for name in names],
                migrations=migrations,
                files=sorted(changed),
                dry_run=dry_run,
            )
            needs_install = any(source[name] != target[name] for name in names)
            if not changed and not needs_install:
                report.message = "Tooling is already up to date"
                return report
            history = json.loads(
                original[".womm-update.json"] or b'{"schema_version":1,"updates":[]}'
            )
            if history.get("schema_version") != 1 or not isinstance(
                history.get("updates"), list
            ):
                raise ProjectServiceError(
                    "tooling_update", "Unsupported tooling update history"
                )
            history["updates"].append(
                {
                    "id": uuid4().hex,
                    "womm_version": __version__,
                    "template": template.qualified_id,
                    "template_version": template.version,
                    "source": source,
                    "target": target,
                    "migrations": migrations,
                }
            )
            changed[".womm-update.json"] = (
                json.dumps(history, indent=2) + "\n"
            ).encode()
            report.files = sorted(changed)
            if dry_run:
                report.message = (
                    "Preview complete; project files and environment were not changed"
                )
                return report
            if approve is not None and not approve(report):
                report.message = "Tooling update cancelled"
                return report
            self._apply(project, stage, environment, names, original, changed, report)
            return report

    @staticmethod
    def _apply(
        project: Path,
        stage: Path,
        environment: ToolingEnvironment,
        names: list[str],
        original: dict[str, bytes | None],
        changed: dict[str, bytes],
        report: ToolingUpdateResult,
    ) -> None:
        lock = confined(project, ".womm-update.lock")
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise ProjectServiceError(
                "tooling_update",
                "Another update is running, or .womm-update.lock needs manual inspection",
            ) from exc
        os.close(descriptor)
        try:
            for name, content in original.items():
                path = confined(project, name)
                if (path.read_bytes() if path.is_file() else None) != content:
                    raise ProjectServiceError(
                        "tooling_update",
                        "Project files changed while the plan was prepared; run the update again",
                    )
            backup = confined(project, f".womm-backups/update/{uuid4().hex}")
            backup.mkdir(parents=True)
            for name in changed:
                content = original[name]
                if content is not None:
                    (backup / name).write_bytes(content)
            (backup / "manifest.json").write_text(
                json.dumps(
                    {
                        "files": list(changed),
                        "previously_absent": [
                            name for name in changed if original[name] is None
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            report.backup_path = backup
            try:
                for name, content in changed.items():
                    if name != ".womm-update.json":
                        write_atomic(confined(project, name), content)
                environment.synchronize(project, stage, names)
                write_atomic(
                    confined(project, ".womm-update.json"), changed[".womm-update.json"]
                )
            except BaseException as exc:
                failed = []
                for name in changed:
                    try:
                        path = confined(project, name)
                        content = original[name]
                        if content is None:
                            path.unlink(missing_ok=True)
                        else:
                            write_atomic(path, content)
                    except (OSError, ProjectServiceError):
                        failed.append(name)
                if failed:
                    raise ProjectServiceError(
                        "tooling_update",
                        f"Update failed and some files could not be restored: {', '.join(failed)}. Restore them from {backup.relative_to(project)} and synchronize the environment.",
                    ) from exc
                raise ProjectServiceError(
                    "tooling_update",
                    "Update failed: original files restored. The environment may be partially updated; synchronize it using the restored manifest/lockfile. A backup was retained.",
                ) from exc
            report.files = sorted(changed)
            report.message = "Tooling updated and configuration validated"
        finally:
            lock.unlink(missing_ok=True)
