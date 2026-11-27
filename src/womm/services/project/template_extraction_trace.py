#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE EXTRACTION TRACE - What a template was extracted from
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""The trace ``template init --from`` leaves at the root of a template.

It records where the template was extracted from, with what exclusions and
variables, and the content each project file produced. ``template update``
compares the project, the template and this trace to tell the author's own
edits from the project's changes. The trace lives outside the template's
``_subdirectory``, so it is never rendered into a project.

It is generated state: reading it is strict, and an invalid trace is an
error, never taken as "no trace".
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath

from womm.exceptions.project import ProjectServiceError

# ///////////////////////////////////////////////////////////////
# CONSTANTS
# ///////////////////////////////////////////////////////////////

TRACE_FILENAME = ".womm-extract.json"
TRACE_SCHEMA = 1
HEX64 = re.compile(r"[0-9a-f]{64}")

# ///////////////////////////////////////////////////////////////
# MODELS
# ///////////////////////////////////////////////////////////////


@dataclass(frozen=True)
class TracedFile:
    """What one project file last produced in the template."""

    target: PurePosixPath  # relative to the template's _subdirectory
    sha256: str  # of the last candidate content seen
    # Where the author kept the file when it differs from ``target``: a
    # conflict settled by keeping a file that the project now names otherwise.
    path: PurePosixPath | None = None

    @property
    def location(self) -> PurePosixPath:
        """Where the file lives in the template."""
        return self.path or self.target


@dataclass
class ExtractionTrace:
    """Provenance and baseline of an extracted template."""

    origin: str | None  # POSIX path from the template to the project
    excludes: list[str] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)
    contract: dict[str, object] = field(default_factory=dict)
    files: dict[PurePosixPath, TracedFile] = field(default_factory=dict)


# ///////////////////////////////////////////////////////////////
# FUNCTIONS
# ///////////////////////////////////////////////////////////////


def digest(content: bytes) -> str:
    """Hash recorded for a file content."""
    return hashlib.sha256(content).hexdigest()


def relative_origin(template: Path, project: Path) -> str | None:
    """POSIX path from ``template`` to ``project``, or None across drives."""
    try:
        return Path(os.path.relpath(project.resolve(), template.resolve())).as_posix()
    except ValueError:
        return None


def location_problem(files: dict[PurePosixPath, TracedFile]) -> str | None:
    """Why ``files`` cannot be a trace's files, or None.

    Each project file owns one path of the template: two cannot share it, and
    one cannot be the directory of another.
    """
    owners: dict[str, PurePosixPath] = {}
    for source, item in files.items():
        key = item.location.as_posix().casefold()
        other = owners.setdefault(key, source)
        if other != source:
            return f"{source} and {other} share the path {item.location}"
    for key in owners:
        if any(parent.as_posix() in owners for parent in PurePosixPath(key).parents):
            return f"a path is also a directory: {key}"
    return None


def write_trace(template: Path, trace: ExtractionTrace) -> None:
    """Write ``trace`` at the root of ``template``, atomically."""
    payload = {
        "schema_version": TRACE_SCHEMA,
        "from": trace.origin,
        "excludes": trace.excludes,
        "variables": trace.variables,
        "contract": trace.contract,
        "files": {
            source.as_posix(): {
                "target": item.target.as_posix(),
                "sha256": item.sha256,
                **({"path": item.path.as_posix()} if item.path else {}),
            }
            for source, item in sorted(trace.files.items())
        },
    }
    handle, temp = tempfile.mkstemp(
        dir=template, prefix=".womm-extract-", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
        os.replace(temp, template / TRACE_FILENAME)
    except OSError:
        Path(temp).unlink(missing_ok=True)
        raise


def read_trace(template: Path) -> ExtractionTrace | None:
    """Read the trace of ``template``; None when it has none.

    Raises:
        ProjectServiceError: If the trace exists but is invalid.
    """
    path = template / TRACE_FILENAME
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise _invalid(path, "not a regular file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _invalid(path, str(exc)) from exc
    schema = payload.get("schema_version") if isinstance(payload, dict) else None
    if type(schema) is not int or schema != TRACE_SCHEMA:
        raise _invalid(path, "unknown schema")
    origin = payload.get("from")
    excludes = payload.get("excludes")
    variables = payload.get("variables")
    contract = payload.get("contract")
    files = payload.get("files")
    if not (
        (origin is None or _relative_origin(origin))
        and isinstance(excludes, list)
        and all(isinstance(e, str) for e in excludes)
        and isinstance(variables, dict)
        and all(isinstance(k, str) and isinstance(v, str) for k, v in variables.items())
        and isinstance(contract, dict)
        and isinstance(files, dict)
    ):
        raise _invalid(path, "unexpected content")
    traced: dict[PurePosixPath, TracedFile] = {}
    for source, item in files.items():
        if not (
            isinstance(item, dict)
            and isinstance(item.get("target"), str)
            and isinstance(item.get("sha256"), str)
            and HEX64.fullmatch(item["sha256"])
        ):
            raise _invalid(path, f"unexpected entry for {source}")
        target = _confined(path, item["target"])
        kept = _confined(path, item["path"]) if "path" in item else None
        traced[_confined(path, source)] = TracedFile(
            target=target, sha256=item["sha256"], path=kept
        )
    problem = location_problem(traced)
    if problem:
        raise _invalid(path, problem)
    return ExtractionTrace(
        origin=origin,
        excludes=list(excludes),
        variables=dict(variables),
        contract=dict(contract),
        files=traced,
    )


# ///////////////////////////////////////////////////////////////
# HELPER FUNCTIONS
# ///////////////////////////////////////////////////////////////


def _confined(path: Path, value: object) -> PurePosixPath:
    """A relative path that cannot leave the directory it is relative to."""
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise _invalid(path, f"invalid path {value!r}")
    rel = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        rel.is_absolute()
        or windows.drive
        or windows.root
        or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise _invalid(path, f"path escapes the template: {value}")
    return rel


def _relative_origin(value: object) -> bool:
    """A relative POSIX path, which may climb out of the template with '..'."""
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        return False
    windows = PureWindowsPath(value)
    return not (PurePosixPath(value).is_absolute() or windows.drive or windows.root)


def _invalid(path: Path, details: str) -> ProjectServiceError:
    return ProjectServiceError(
        operation="read_extraction_trace",
        reason=f"Extraction trace is invalid: {path}",
        details=details,
    )


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "TRACE_FILENAME",
    "ExtractionTrace",
    "TracedFile",
    "digest",
    "location_problem",
    "read_trace",
    "relative_origin",
    "write_trace",
]
