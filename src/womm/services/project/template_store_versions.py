#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE STORE VERSIONS - Versioned copies of user templates
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Versioned copies of user templates inside WOMM's store.

A template's copy lives in a stable directory holding ``manifest.json`` and
one directory per version, ``v1/`` to ``vN/``. The manifest alone says which
version is current: it is the commit point of every publication, replaced
atomically once the new version is complete. Every version is kept.

Copies made before versioning sit flat in the stable directory. They stay
usable as they are and become ``v1`` at their next publication.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from womm.exceptions.project import ProjectServiceError

# ///////////////////////////////////////////////////////////////
# CONSTANTS
# ///////////////////////////////////////////////////////////////

MANIFEST_FILENAME = "manifest.json"
MANIFEST_SCHEMA = 1
VERSION_DIR = re.compile(r"v([1-9][0-9]*)")
HEX64 = re.compile(r"[0-9a-f]{64}")
LOCK_SUFFIX = ".lock"

# A template's history is not part of it.
IGNORED_NAMES = frozenset({".git"})

# ///////////////////////////////////////////////////////////////
# MODELS
# ///////////////////////////////////////////////////////////////


@dataclass(frozen=True)
class StoreState:
    """Where a stored template renders from."""

    source: Path
    current: int = 0  # 0: flat copy made before versioning
    count: int = 0


@dataclass(frozen=True)
class Publication:
    """Outcome of :func:`publish`."""

    state: StoreState
    created: bool


# ///////////////////////////////////////////////////////////////
# FUNCTIONS
# ///////////////////////////////////////////////////////////////


def read_state(root: Path) -> StoreState:
    """Tell which directory of ``root`` a template renders from.

    Args:
        root: Stable directory of a stored template.

    Returns:
        StoreState: The current version, or the flat legacy copy.

    Raises:
        ProjectServiceError: If ``manifest.json`` exists but is invalid.
    """
    manifest = _read_manifest(root)
    if manifest is None:
        return StoreState(source=root)
    current = manifest["current"]
    source = root / f"v{current}"
    if source.is_symlink() or source.is_junction():
        raise _invalid(root, f"v{current} is a link")
    return StoreState(source=source, current=current, count=len(manifest["versions"]))


def publish(
    root: Path,
    origin: Path,
    has_manifest: Callable[[Path], bool],
    template_version: str = "",
) -> Publication:
    """Copy ``origin`` as the next version of the template stored in ``root``.

    No version is created when the copy is identical to the current version
    as it stands on disk: a damaged current version is never taken as equal.
    The caller holds the lock of ``root``.

    Args:
        root: Stable directory of the stored template, created if missing.
        origin: Template directory to copy.
        has_manifest: Callable telling whether a directory holds a Copier
            manifest.
        template_version: ``_womm.version`` of the copied template.

    Returns:
        Publication: The state left by this publication.

    Raises:
        ProjectServiceError: If the store is invalid or not writable.
    """
    root.parent.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest(root)
    if manifest is None and has_manifest(root):
        manifest = _migrate_flat(root)
    manifest = manifest or {"schema_version": MANIFEST_SCHEMA, "versions": []}
    staging = Path(tempfile.mkdtemp(dir=root.parent, prefix=f".{root.name}-"))
    try:
        fresh = staging / "fresh"
        _copy_tree(origin, fresh)
        digest = tree_hash(fresh)
        number = manifest.get("current")
        current = root / f"v{number}"
        if number and current.is_dir() and tree_hash(current) == digest:
            return Publication(read_state(root), created=False)
        versions = manifest["versions"]
        number = _next_number(root, versions)
        root.mkdir(exist_ok=True)
        fresh.rename(root / f"v{number}")
        versions.append(
            {
                "number": number,
                "template_version": template_version,
                "created": datetime.now(UTC).isoformat(timespec="seconds"),
                "copied_from": str(origin),
                "tree_hash": digest,
            }
        )
        manifest["current"] = number
        _write_manifest(root, manifest)
    except OSError as exc:
        raise ProjectServiceError(
            operation="copy_template",
            reason=f"Template could not be copied into WOMM: {origin}",
            details=str(exc),
        ) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return Publication(read_state(root), created=True)


def discard(root: Path) -> Path | None:
    """Move a stored template out of the store; the caller holds its lock.

    The move is atomic: once it returns, nothing renders from ``root`` any
    more. Delete the returned directory with :func:`purge`.

    Returns:
        Path | None: Where the template went, None if there was nothing.

    Raises:
        ProjectServiceError: If the template cannot be moved.
    """
    if not root.exists():
        return None
    trash = Path(tempfile.mkdtemp(dir=root.parent, prefix=f".{root.name}-removed-"))
    try:
        root.rename(trash / root.name)
    except OSError as exc:
        trash.rmdir()
        raise ProjectServiceError(
            operation="remove_template",
            reason=f"Stored template could not be removed: {root}",
            details=str(exc),
        ) from exc
    return trash


def purge(trash: Path | None) -> None:
    """Delete what :func:`discard` moved aside, as far as the disk allows."""
    if trash is not None:
        shutil.rmtree(trash, ignore_errors=True)


def remove(root: Path) -> None:
    """Delete a stored template and all its versions; the caller holds its lock."""
    purge(discard(root))


@contextmanager
def locked(path: Path) -> Generator[None]:
    """Hold an exclusive lock on ``path``, or fail at once.

    The lock is a sibling directory whose name starts with a dot, which no
    template identifier can.
    """
    lock = path.with_name(f".{path.name}{LOCK_SUFFIX}")
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise ProjectServiceError(
            operation="lock_template",
            reason=f"Another WOMM command is changing templates: {path.name}",
            details=f"If none is running, delete {lock}",
        ) from exc
    try:
        yield
    finally:
        lock.rmdir()


def tree_hash(root: Path) -> str:
    """Hash a directory: paths, kinds, executable bits and contents."""
    digest = hashlib.sha256()
    for path in sorted(_walk(root), key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            entry = f"l {rel} {os.readlink(path)}"
        elif path.is_dir():
            entry = f"d {rel}"
        else:
            content = hashlib.sha256(path.read_bytes()).hexdigest()
            executable = int(os.access(path, os.X_OK) and os.name != "nt")
            entry = f"f {rel} {executable} {content}"
        digest.update(entry.encode("utf-8") + b"\0")
    return digest.hexdigest()


# ///////////////////////////////////////////////////////////////
# HELPER FUNCTIONS
# ///////////////////////////////////////////////////////////////


def _read_manifest(root: Path) -> dict[str, Any] | None:
    path = root / MANIFEST_FILENAME
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise _invalid(root, "not a regular file")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _invalid(root, str(exc)) from exc
    if not _valid_manifest(manifest):
        raise _invalid(root, "unexpected content")
    return manifest


def _valid_manifest(manifest: object) -> bool:
    if not isinstance(manifest, dict):
        return False
    schema = manifest.get("schema_version")
    versions = manifest.get("versions")
    current = manifest.get("current")
    if type(schema) is not int or schema != MANIFEST_SCHEMA:
        return False
    if not isinstance(versions, list) or not versions:
        return False
    if not all(
        isinstance(v, dict)
        and type(v.get("number")) is int
        and v["number"] > 0
        and isinstance(v.get("tree_hash"), str)
        and HEX64.fullmatch(v["tree_hash"])
        for v in versions
    ):
        return False
    numbers = [v["number"] for v in versions]
    return (
        len(set(numbers)) == len(numbers)
        and type(current) is int
        and current in numbers
    )


def _write_manifest(root: Path, manifest: dict[str, Any]) -> None:
    handle, temp = tempfile.mkstemp(dir=root, prefix=".manifest-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(manifest, stream, indent=2)
        os.replace(temp, root / MANIFEST_FILENAME)
    except OSError:
        Path(temp).unlink(missing_ok=True)
        raise


def _migrate_flat(root: Path) -> dict[str, Any]:
    """Turn a flat legacy copy into ``v1``, keeping it usable until committed."""
    legacy = [
        entry for entry in root.iterdir() if not entry.name.startswith(".manifest-")
    ]
    if any(VERSION_DIR.fullmatch(entry.name) for entry in legacy):
        # A crash between v1 and its manifest, or a template file named v1.
        raise ProjectServiceError(
            operation="copy_template",
            reason=f"Stored template cannot be versioned: {root}",
            details="It already holds a v<number> entry. Move it aside, then retry.",
        )
    staging = Path(tempfile.mkdtemp(dir=root.parent, prefix=f".{root.name}-"))
    created = None
    try:
        version = staging / "v1"
        version.mkdir()
        for entry in legacy:
            if entry.is_dir() and not entry.is_symlink():
                _copy_tree(entry, version / entry.name)
            else:
                shutil.copy2(entry, version / entry.name, follow_symlinks=False)
        manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "current": 1,
            "versions": [
                {
                    "number": 1,
                    "template_version": "",
                    "created": datetime.now(UTC).isoformat(timespec="seconds"),
                    "copied_from": None,
                    "tree_hash": tree_hash(version),
                }
            ],
        }
        created = root / "v1"
        version.rename(created)
        _write_manifest(root, manifest)
    except OSError as exc:
        # Only the v1 this attempt created: the flat copy is still current.
        if created is not None:
            shutil.rmtree(created, ignore_errors=True)
        raise ProjectServiceError(
            operation="copy_template",
            reason=f"Stored template could not be versioned: {root}",
            details=str(exc),
        ) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    # The manifest is committed: the flat copy is no longer what renders.
    for entry in legacy:
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)
    return manifest


def _next_number(root: Path, versions: list[dict[str, Any]]) -> int:
    """First number above every known version, including orphan directories."""
    numbers = [v["number"] for v in versions]
    if root.is_dir():
        numbers += [
            int(match.group(1))
            for entry in root.iterdir()
            if (match := VERSION_DIR.fullmatch(entry.name))
        ]
    return max(numbers, default=0) + 1


def _copy_tree(origin: Path, target: Path) -> None:
    shutil.copytree(
        origin, target, symlinks=True, ignore=shutil.ignore_patterns(*IGNORED_NAMES)
    )


def _walk(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if not IGNORED_NAMES.intersection(path.relative_to(root).parts):
            yield path


def _invalid(root: Path, details: str) -> ProjectServiceError:
    return ProjectServiceError(
        operation="load_catalog",
        reason=f"Stored template manifest is invalid: {root / MANIFEST_FILENAME}",
        details=details,
    )


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "MANIFEST_FILENAME",
    "Publication",
    "StoreState",
    "locked",
    "discard",
    "publish",
    "purge",
    "read_state",
    "remove",
    "tree_hash",
]
