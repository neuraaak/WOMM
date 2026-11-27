#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE UPDATE SERVICE - Bring an extracted template up to date
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Update a template extracted from a project with the project's changes.

Three states of each project file are compared: the content the last
extraction produced (B, from the trace), the file in the template now (M)
and the content a new extraction produces (N). A change made only in the
project is applied, a change made only in the template is kept, and what
the author must decide is returned as a question: a file new in the project,
a file gone from it, or a change on both sides.

Planning writes nothing. Applying re-checks every file against the plan,
writes everything or restores everything, then records the new baseline.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
import json
import os
import re
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import yaml

from womm.exceptions.project import ProjectServiceError
from womm.shared.results.template_results import (
    ChangeKind,
    FileChange,
    TemplateExtractionReport,
    UpdateOutcome,
)

from .template_extraction_service import (
    CONTRACT,
    DELIMITERS,
    TEMPLATE_SUBDIRECTORY,
    TEMPLATE_SUFFIX,
    ExtractedFile,
    TemplateExtractionService,
    canonical,
)
from .template_extraction_trace import (
    TRACE_FILENAME,
    ExtractionTrace,
    TracedFile,
    digest,
    location_problem,
    read_trace,
    relative_origin,
    write_trace,
)

# ///////////////////////////////////////////////////////////////
# CONSTANTS
# ///////////////////////////////////////////////////////////////

MANIFESTS = ("copier.yml", "copier.yaml")
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
VERSION_LINE = re.compile(
    r"^(?P<lead>[ \t]+version:[ \t]*)(?P<quote>[\"']?)(?P<value>[^\"'#\s]+)(?P=quote)"
)

# ///////////////////////////////////////////////////////////////
# MODELS
# ///////////////////////////////////////////////////////////////


@dataclass
class UpdatePlan:
    """Everything an update would do, computed without writing."""

    template: Path
    project: Path
    manifest: Path
    changes: list[FileChange] = field(default_factory=list)
    unchanged: int = 0
    kept: int = 0
    report: TemplateExtractionReport = field(default_factory=TemplateExtractionReport)
    # Baseline entries whatever the decisions are.
    base: dict[PurePosixPath, TracedFile] = field(default_factory=dict)
    previous: ExtractionTrace | None = None
    origin: str | None = None
    # Hash of every template file the plan read, None when absent.
    seen: dict[PurePosixPath, str | None] = field(default_factory=dict)
    manifest_bytes: bytes = b""
    trace_bytes: bytes = b""
    # Files under the template's _subdirectory when the plan was made.
    existing: set[PurePosixPath] = field(default_factory=set)

    def questions(self) -> list[FileChange]:
        """Changes the author decides on."""
        return [c for c in self.changes if c.kind is not ChangeKind.UPDATED]


# ///////////////////////////////////////////////////////////////
# SERVICE
# ///////////////////////////////////////////////////////////////


class TemplateUpdateService:
    """Plan and apply the update of an extracted template from its project."""

    def __init__(self) -> None:
        self._extractor = TemplateExtractionService()

    # ///////////////////////////////////////////////////////////
    # PUBLIC METHODS
    # ///////////////////////////////////////////////////////////

    def has_trace(self, template: Path) -> bool:
        """Tell whether ``template`` was extracted from a project."""
        return read_trace(template) is not None

    def plan(self, template: Path, project: Path | None = None) -> UpdatePlan:
        """Compare the template with a new extraction of its project.

        Args:
            template: Template root, holding ``copier.yml`` and the trace.
            project: Project to extract from; defaults to the trace's origin.

        Returns:
            UpdatePlan: The changes, and the questions they raise.

        Raises:
            ProjectServiceError: When the update must be refused.
        """
        template = template.resolve()
        trace_path = template / TRACE_FILENAME
        _check_no_link(template, trace_path)
        trace = read_trace(template)
        if trace is None:
            raise _refuse(
                "This template has no extraction trace",
                details="Create it again with womm template init --from in a new"
                " folder, then carry your own questions over.",
            )
        if project is None:
            if trace.origin is None:
                raise _refuse(
                    "The trace does not say where the project is",
                    details="Pass it with --from PROJECT.",
                )
            project = template / trace.origin
        project = project.resolve()
        manifest = _manifest(template)
        _check_contract(manifest, trace)
        template_dir = template / TEMPLATE_SUBDIRECTORY
        _check_no_link(template, template_dir)

        extraction = self._extractor.plan(project, template, trace.excludes)
        if extraction.report.variables != trace.variables:
            raise _refuse(
                "The project's identity changed since the extraction",
                details=f"Was {trace.variables}, is now"
                f" {extraction.report.variables}. Create a new template in an"
                " empty folder and carry your questions over.",
            )

        plan = UpdatePlan(
            template=template,
            project=project,
            manifest=manifest,
            report=extraction.report,
            previous=trace,
            origin=relative_origin(template, project),
            manifest_bytes=manifest.read_bytes(),
            trace_bytes=trace_path.read_bytes(),
            existing=_files_under(template_dir),
        )
        incoming = {item.source: item for item in extraction.files}
        for source in sorted(set(trace.files) | set(incoming)):
            self._classify(
                plan,
                template_dir,
                source,
                trace.files.get(source),
                incoming.get(source),
            )
        return plan

    def apply(
        self, plan: UpdatePlan, decisions: Mapping[PurePosixPath, bool]
    ) -> UpdateOutcome:
        """Apply ``plan``: every automatic change, and each decided question.

        A question absent from ``decisions`` stays pending: nothing changes
        for it and the next update asks again.

        Args:
            plan: Result of :meth:`plan`.
            decisions: For each question's source, True to take the project's
                side (integrate, delete, take the new content), False to keep
                the template as it is.

        Returns:
            UpdateOutcome: What was written, removed and left pending.

        Raises:
            ProjectServiceError: If the template changed since the plan, or
                the update could not be written.
        """
        try:
            return self._apply(plan, decisions)
        except OSError as exc:
            raise _refuse(
                "The template could not be updated", details=str(exc)
            ) from exc

    # ///////////////////////////////////////////////////////////
    # PRIVATE METHODS
    # ///////////////////////////////////////////////////////////

    def _apply(
        self, plan: UpdatePlan, decisions: Mapping[PurePosixPath, bool]
    ) -> UpdateOutcome:
        template_dir = plan.template / TEMPLATE_SUBDIRECTORY
        writes: dict[PurePosixPath, FileChange] = {}
        deletes: set[PurePosixPath] = set()
        base = dict(plan.base)
        pending: list[str] = []
        for change in plan.changes:
            taken = (
                True
                if change.kind is ChangeKind.UPDATED
                else decisions.get(change.source)
            )
            _record_base(base, change, taken, plan.previous)
            if taken is None:
                pending.append(change.source.as_posix())
            if not taken:
                continue
            if change.target is not None and change.content is not None:
                writes[change.target] = change
            if change.current is not None and change.current != change.target:
                deletes.add(change.current)
            if change.content is None and change.current is not None:
                deletes.add(change.current)
        deletes -= set(writes)
        _settle_ownership(base, plan.previous)

        # Only an effective change of the template's files bumps its version.
        written = [
            p
            for p, change in writes.items()
            if plan.seen.get(p) != digest(change.content or b"")
        ]
        removed = sorted(p for p in deletes if plan.seen.get(p) is not None)
        manifest_bytes = None
        version = None
        if written or removed:
            manifest_bytes, version = _bump_patch(plan.manifest_bytes)

        self._revalidate(plan, template_dir, set(writes) | deletes)
        _check_final_tree(_files_under(template_dir) - deletes | set(writes))
        trace = ExtractionTrace(
            origin=plan.origin,
            excludes=list(plan.previous.excludes) if plan.previous else [],
            variables=dict(plan.report.variables),
            contract=dict(CONTRACT),
            files=base,
        )
        touched = [template_dir / p for p in sorted(set(writes) | deletes)]
        touched += [plan.manifest, plan.template / TRACE_FILENAME]
        with _Transaction(touched):
            for path in sorted(deletes):
                _delete(template_dir, template_dir / path)
            for path, change in sorted(writes.items()):
                target = template_dir / path
                created = not target.exists()
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(change.content or b"")
                if created and change.mode:
                    # A new file takes the project's permissions; an existing
                    # one keeps the author's.
                    os.chmod(target, change.mode)
            if manifest_bytes is not None:
                plan.manifest.write_bytes(manifest_bytes)
            write_trace(plan.template, trace)
        return UpdateOutcome(
            written=sorted(p.as_posix() for p in written),
            removed=[p.as_posix() for p in removed],
            pending=pending,
            version=version,
        )

    def _classify(
        self,
        plan: UpdatePlan,
        template_dir: Path,
        source: PurePosixPath,
        before: TracedFile | None,
        after: ExtractedFile | None,
    ) -> None:
        """Sort one project file into unchanged, kept, automatic or question."""
        new = digest(after.content) if after else None
        if before is None:
            assert after is not None and new is not None
            clash = self._clash(plan, after.target, exclude=None)
            if clash is None:
                self._seen(plan, template_dir, after.target)
                plan.changes.append(_change(source, ChangeKind.NEW, None, after))
            elif clash == after.target and self._seen(plan, template_dir, clash) == new:
                plan.unchanged += 1
                plan.base[source] = TracedFile(after.target, new)
            else:
                self._seen(plan, template_dir, after.target)
                self._seen(plan, template_dir, clash)
                plan.changes.append(
                    _change(
                        source,
                        ChangeKind.CONFLICT,
                        clash,
                        after,
                        f"a file of yours renders to the same path: {clash}",
                    )
                )
            return

        here = before.location
        current = self._seen(plan, template_dir, here)
        untouched = current == before.sha256 and here == before.target
        if after is None:
            if current is None:
                return  # gone from both sides
            kind = ChangeKind.REMOVABLE if untouched else ChangeKind.CONFLICT
            reason = (
                ""
                if untouched
                else "removed from the project, kept or edited in the template"
            )
            plan.changes.append(_change(source, kind, here, None, reason))
            return

        assert new is not None
        self._seen(plan, template_dir, after.target)
        if current == new and after.target == here:
            plan.unchanged += 1
            plan.base[source] = TracedFile(after.target, new)
            return
        if (after.target, new) == (before.target, before.sha256):
            plan.kept += 1  # the author's edit, move or deletion
            plan.base[source] = before
            return
        if current is None:
            plan.changes.append(
                _change(
                    source,
                    ChangeKind.CONFLICT,
                    None,
                    after,
                    "deleted from the template, changed in the project",
                )
            )
            return
        if untouched or current == new:
            # Changed in the project only, or renamed because the file starts
            # or stops holding the project's name.
            clash = self._clash(plan, after.target, exclude=here)
            if clash is not None:
                raise _refuse(
                    f"{source} would render over your file {clash}",
                    details="Rename or delete that file, then run the update again.",
                )
            plan.changes.append(_change(source, ChangeKind.UPDATED, here, after))
            return
        plan.changes.append(
            _change(
                source,
                ChangeKind.CONFLICT,
                here,
                after,
                "changed in the project and in the template",
            )
        )

    def _clash(
        self,
        plan: UpdatePlan,
        target: PurePosixPath,
        exclude: PurePosixPath | None,
    ) -> PurePosixPath | None:
        """The existing file ``target`` renders over, if any.

        Raises:
            ProjectServiceError: If ``target`` and an existing path would be a
                file and a directory at once.
        """
        key = canonical(target)
        found = None
        for path in plan.existing:
            if path == exclude:
                continue
            other = canonical(path)
            if other == key:
                found = path if found is None or path == target else found
            elif other.startswith(key + "/") or key.startswith(other + "/"):
                raise _refuse(
                    f"{target} and {path} would be a file and a directory at once",
                    details="Rename or delete one of them, then run the update again.",
                )
        return found

    def _seen(
        self, plan: UpdatePlan, template_dir: Path, rel: PurePosixPath
    ) -> str | None:
        if rel not in plan.seen:
            path = template_dir / rel
            _check_no_link(template_dir, path)
            plan.seen[rel] = digest(path.read_bytes()) if path.is_file() else None
        return plan.seen[rel]

    def _revalidate(
        self, plan: UpdatePlan, template_dir: Path, paths: set[PurePosixPath]
    ) -> None:
        """Refuse to write over what changed since the plan was shown."""
        for path in [plan.manifest, plan.template / TRACE_FILENAME]:
            _check_no_link(plan.template, path)
        for p in paths:
            _check_no_link(template_dir, template_dir / p)
        changed = [
            p.as_posix()
            for p in sorted(paths)
            if _hash_of(template_dir / p) != plan.seen.get(p)
        ]
        if _bytes_of(plan.manifest) != plan.manifest_bytes:
            changed.append(plan.manifest.name)
        if _bytes_of(plan.template / TRACE_FILENAME) != plan.trace_bytes:
            changed.append(TRACE_FILENAME)
        if changed:
            raise _refuse(
                "The template changed since the update was planned",
                details=f"Changed: {', '.join(changed)}. Run the update again.",
            )


# ///////////////////////////////////////////////////////////////
# HELPER FUNCTIONS
# ///////////////////////////////////////////////////////////////


def _change(
    source: PurePosixPath,
    kind: ChangeKind,
    current: PurePosixPath | None,
    after: ExtractedFile | None,
    reason: str = "",
) -> FileChange:
    return FileChange(
        source=source,
        kind=kind,
        current=current,
        target=after.target if after else None,
        content=after.content if after else None,
        reason=reason,
        mode=after.mode if after else 0,
    )


def _record_base(
    base: dict[PurePosixPath, TracedFile],
    change: FileChange,
    taken: bool | None,
    previous: ExtractionTrace | None,
) -> None:
    """Baseline after a decision: a pending question keeps the old one."""
    before = previous.files.get(change.source) if previous else None
    explicit = taken is not None
    if change.kind is ChangeKind.NEW:
        if taken and change.target is not None and change.content is not None:
            base[change.source] = TracedFile(change.target, digest(change.content))
        return
    if change.content is None:  # gone from the project
        # Deleting resolves it; so does keeping an edited file on purpose.
        # Otherwise the next update proposes the deletion again.
        resolved = taken or (explicit and change.kind is ChangeKind.CONFLICT)
        if not resolved and before is not None:
            base[change.source] = before
        return
    if change.kind is ChangeKind.CONFLICT and not explicit:
        if before is not None:
            base[change.source] = before
        return
    assert change.target is not None
    if taken:
        base[change.source] = TracedFile(change.target, digest(change.content))
        return
    # Kept on purpose: the file stays where it is, and this content of the
    # project counts as seen.
    kept = change.current if change.current not in (None, change.target) else None
    if kept is None and change.current is None and before is not None:
        kept = before.path
    base[change.source] = TracedFile(change.target, digest(change.content), kept)


def _settle_ownership(
    base: dict[PurePosixPath, TracedFile], previous: ExtractionTrace | None
) -> None:
    """Give each template path back to the project file that already owned it.

    A file kept against a newcomer stays its previous owner's: the newcomer is
    not adopted, and the next update asks again. Anything else that would
    leave an unreadable trace is refused before any write.
    """
    owners: dict[str, list[PurePosixPath]] = {}
    for source, item in base.items():
        owners.setdefault(item.location.as_posix().casefold(), []).append(source)
    for sources in owners.values():
        if len(sources) < 2:
            continue
        for source in sources:
            before = previous.files.get(source) if previous else None
            if before is None or before.location != base[source].location:
                del base[source]
    problem = location_problem(base)
    if problem:
        raise _refuse(
            "These decisions leave two project files on one template path",
            details=f"{problem}. Decide otherwise for one of them.",
        )


def _files_under(root: Path) -> set[PurePosixPath]:
    if not root.is_dir():
        return set()
    return {
        PurePosixPath(path.relative_to(root).as_posix())
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }


def _check_final_tree(files: set[PurePosixPath]) -> None:
    """Refuse a template whose files would render over one another."""
    keys: dict[str, PurePosixPath] = {}
    for path in sorted(files):
        clash = keys.setdefault(canonical(path), path)
        if clash != path:
            raise _refuse(
                f"{path} and {clash} would render to the same path",
                details="Decide otherwise, or rename one of them.",
            )
    for path in files:
        for parent in path.parents:
            if parent.parts and canonical(parent) in keys:
                raise _refuse(f"{keys[canonical(parent)]} would also be a directory")


def _manifest(template: Path) -> Path:
    for name in MANIFESTS:
        path = template / name
        if path.exists() or path.is_symlink():
            _check_no_link(template, path)
            if path.is_file():
                return path
    raise _refuse(f"Not a Copier template: {template}")


def _check_contract(manifest: Path, trace: ExtractionTrace) -> None:
    """The settings and questions the trace relies on must still be there."""
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8-sig")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise _refuse(f"{manifest.name} cannot be read", details=str(exc)) from exc
    envops = data.get("_envops") if isinstance(data, dict) else None
    if (
        not isinstance(data, dict)
        or data.get("_subdirectory") != TEMPLATE_SUBDIRECTORY
        or data.get("_templates_suffix") != TEMPLATE_SUFFIX
        or not isinstance(envops, dict)
        or any(envops.get(key) != value for key, value in DELIMITERS.items())
    ):
        raise _refuse(
            f"{manifest.name} no longer matches its extraction",
            details="_subdirectory, _templates_suffix and _envops must stay as"
            " template init --from wrote them.",
        )
    # The generated questions chain: package_name derives from project_slug,
    # which derives from project_name, whichever of them the trace recorded.
    needed = set(trace.variables)
    if needed:
        needed |= {"project_name", "project_slug"}
    missing = sorted(name for name in needed if name not in data)
    if missing:
        raise _refuse(
            f"{manifest.name} lacks questions the template uses: {', '.join(missing)}",
            details="Put them back as template init --from wrote them.",
        )


def _check_no_link(root: Path, path: Path) -> None:
    current = path
    while True:
        if current.is_symlink() or current.is_junction():
            raise _refuse(f"{current} is a link: the update does not follow links")
        if current == root or current.parent == current:
            return
        current = current.parent


def _hash_of(path: Path) -> str | None:
    return digest(path.read_bytes()) if path.is_file() else None


def _bytes_of(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _bump_patch(manifest: bytes) -> tuple[bytes, tuple[str, str]]:
    """Raise ``_womm.version`` by one patch, touching only that value.

    Raises:
        ProjectServiceError: If the version is not a plain X.Y.Z in a block
            ``_womm`` mapping.
    """
    bom = manifest.startswith(b"\xef\xbb\xbf")
    text = manifest[3 if bom else 0 :].decode("utf-8")
    try:
        before = (yaml.safe_load(text) or {}).get("_womm", {}).get("version")
    except (yaml.YAMLError, AttributeError) as exc:
        raise _refuse("_womm.version cannot be read", details=str(exc)) from exc
    match = SEMVER.fullmatch(str(before)) if isinstance(before, str) else None
    if match is None:
        raise _refuse(
            f"_womm.version is not a plain X.Y.Z version: {before!r}",
            details="Set it by hand, then run the update again.",
        )
    after = f"{match[1]}.{match[2]}.{int(match[3]) + 1}"
    lines = text.splitlines(keepends=True)
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if re.match(r"_womm:[ \t]*(#.*)?\r?\n?$", line)
        ),
        None,
    )
    for index in range(start + 1 if start is not None else len(lines), len(lines)):
        line = lines[index]
        if line.strip() and not line[0].isspace():
            break
        found = VERSION_LINE.match(line)
        if found and found["value"] == before:
            lines[index] = (
                line[: found.start("value")] + after + line[found.end("value") :]
            )
            bumped = "".join(lines)
            if (yaml.safe_load(bumped) or {}).get("_womm", {}).get("version") == after:
                data = bumped.encode("utf-8")
                return (b"\xef\xbb\xbf" + data if bom else data), (before, after)
            break
    raise _refuse(
        "_womm.version could not be raised in place",
        details="Write _womm as a block mapping with a version line, then retry.",
    )


class _Transaction:
    """Back up ``paths``; on OSError, put every one of them back.

    The backup is deleted only once the block succeeded or every file was
    restored: a failed restore keeps it, and says where it is.
    """

    def __init__(self, paths: list[Path]) -> None:
        self._paths = paths
        self._backup = Path(tempfile.mkdtemp(prefix="womm-update-"))
        self._saved: list[tuple[Path, Path | None]] = []

    def __enter__(self) -> None:
        try:
            for index, path in enumerate(self._paths):
                if path.is_file():
                    copy = self._backup / str(index)
                    shutil.copy2(path, copy)
                    self._saved.append((path, copy))
                else:
                    self._saved.append((path, None))
            # Lets the author restore by hand if even the restore fails.
            (self._backup / "recovery.json").write_text(
                json.dumps(
                    [
                        {"backup": copy.name if copy else None, "path": str(path)}
                        for path, copy in self._saved
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            shutil.rmtree(self._backup, ignore_errors=True)
            raise

    def __exit__(self, kind: object, error: object, _tb: object) -> bool:
        if error is None:
            shutil.rmtree(self._backup, ignore_errors=True)
            return False
        failed = []
        for path, copy in self._saved:
            try:
                if copy is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(copy, path)
            except OSError:
                failed.append(path)
        if failed:
            raise _refuse(
                "The template could not be updated, nor fully restored",
                details=f"Not restored: {', '.join(str(p) for p in failed)}."
                f" The previous files are kept in {self._backup}.",
            ) from error if isinstance(error, BaseException) else None
        shutil.rmtree(self._backup, ignore_errors=True)
        if isinstance(error, OSError):
            raise _refuse(
                "The template could not be updated: it was restored",
                details=str(error),
            ) from error
        return False


def _delete(template_dir: Path, path: Path) -> None:
    """Delete a file, then the directories it leaves empty."""
    path.unlink(missing_ok=True)
    parent = path.parent
    while parent != template_dir and parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent


def _refuse(reason: str, details: str = "") -> ProjectServiceError:
    return ProjectServiceError(
        operation="update_template", reason=reason, details=details
    )


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["TemplateUpdateService", "UpdatePlan"]
