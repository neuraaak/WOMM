#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE STORE SERVICE - Copier template catalog
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Catalog of Copier templates known to WOMM.

Official templates ship inside the wheel and are discovered at read time;
they are never written to the user catalog. ``catalog.json`` holds only
user-registered templates, each rendered from a copy WOMM keeps under
``copies/`` so that moving or archiving the original breaks nothing.
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
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from womm.exceptions.project import ProjectServiceError
from womm.shared.models.template_source import TemplateEntry, TemplateOrigin
from womm.shared.paths import (
    packaged_copier_official,
    template_catalog_file,
    user_templates_dir,
)

# ///////////////////////////////////////////////////////////////
# CONSTANTS
# ///////////////////////////////////////////////////////////////

# Manifests a template root may expose, in Copier's lookup order.
TEMPLATE_MANIFESTS = ("copier.yml", "copier.yaml")

# Namespaces a user identifier may not use: they would read as an origin.
RESERVED_NAMESPACES = frozenset(origin.value for origin in TemplateOrigin)

# Each identifier part becomes a directory name: keep it valid on Windows too.
IDENTIFIER_PART = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")
WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"{device}{n}" for device in ("COM", "LPT") for n in range(1, 10)}
)

# Subdirectory of the templates directory holding WOMM's template copies.
COPIES_DIRNAME = "copies"

# Key carrying WOMM metadata inside a template manifest.
WOMM_METADATA_KEY = "_womm"

# Prefixes that mark a source as remote. Remote sources are out of scope
# until an explicit trust model exists.
REMOTE_PREFIXES = (
    "http://",
    "https://",
    "http:/",
    "https:/",
    "http:\\",
    "https:\\",
    "git@",
    "git+",
    "gh:",
    "gl:",
)

# ///////////////////////////////////////////////////////////////
# SERVICE
# ///////////////////////////////////////////////////////////////


class TemplateStoreService:
    """Read and write the template catalog."""

    # ///////////////////////////////////////////////////////////
    # PUBLIC METHODS
    # ///////////////////////////////////////////////////////////

    def list_templates(self) -> list[TemplateEntry]:
        """List every known template, official first.

        Returns:
            list[TemplateEntry]: Entries sorted by qualified identifier.

        Raises:
            ProjectServiceError: If the user catalog cannot be read.
        """
        entries = self._discover_official() + self._load_user_entries()
        return sorted(entries, key=lambda entry: entry.qualified_id)

    def resolve(self, identifier: str) -> TemplateEntry:
        """Resolve an identifier to a single template.

        A qualified identifier (``official/python``) selects one origin. A
        short identifier resolves across origins and fails when ambiguous.

        Args:
            identifier: Qualified or short template identifier.

        Returns:
            TemplateEntry: The matching entry.

        Raises:
            ProjectServiceError: If unknown or ambiguous.
        """
        entries = self.list_templates()

        qualified = [e for e in entries if e.qualified_id == identifier]
        if qualified:
            return qualified[0]

        matches = [e for e in entries if e.id == identifier]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(e.qualified_id for e in matches)
            raise ProjectServiceError(
                operation="resolve_template",
                reason=f"Template identifier is ambiguous: {identifier}",
                details=f"Candidates: {names}. Use a qualified identifier.",
            )
        raise ProjectServiceError(
            operation="resolve_template",
            reason=f"Unknown template: {identifier}",
        )

    def preview(self, identifier: str, source: Path) -> TemplateEntry:
        """Build the entry ``add`` would register, without registering it.

        Args:
            identifier: Short identifier, without any separator.
            source: Directory holding ``copier.yml`` or ``copier.yaml``.

        Returns:
            TemplateEntry: The entry, metadata read from the manifest.

        Raises:
            ProjectServiceError: If the identifier or source is refused.
        """
        self._validate_identifier(identifier, operation="add_template")
        self._validate_source(source, operation="add_template")
        if any(entry.id == identifier for entry in self._load_user_entries()):
            raise ProjectServiceError(
                operation="add_template",
                reason=f"Template already registered: {identifier}",
            )
        return self._build_user_entry(identifier, source)

    def add(self, identifier: str, source: Path) -> TemplateEntry:
        """Copy a local template into WOMM and register it.

        Args:
            identifier: ``name`` or ``namespace/name``.
            source: Directory holding ``copier.yml`` or ``copier.yaml``.

        Returns:
            TemplateEntry: The registered entry, rendered from the copy.

        Raises:
            ProjectServiceError: If the identifier or source is refused, or the
                copy cannot be written.
        """
        entry = self.preview(identifier, source)
        stored = self._store_copy(identifier, entry.source)
        try:
            self._save_user_entries([*self._load_user_entries(), stored])
        except ProjectServiceError:
            shutil.rmtree(stored.source, ignore_errors=True)
            raise
        return stored

    def remove(self, identifier: str) -> TemplateEntry:
        """Unregister a user template and delete WOMM's copy of it.

        The original directory is never touched.

        Args:
            identifier: Qualified or short identifier.

        Returns:
            TemplateEntry: The removed entry.

        Raises:
            ProjectServiceError: If unknown or not user-owned.
        """
        entry = self.resolve(identifier)
        if entry.origin is not TemplateOrigin.USER:
            raise ProjectServiceError(
                operation="remove_template",
                reason=f"Official templates cannot be removed: {identifier}",
            )
        remaining = [item for item in self._load_user_entries() if item.id != entry.id]
        self._save_user_entries(remaining)
        if self._is_copy(entry.source):
            shutil.rmtree(entry.source, ignore_errors=True)
        return entry

    def update(self, identifier: str, source: Path | None = None) -> TemplateEntry:
        """Refresh WOMM's copy of a user template.

        Without ``source``, the copy is refreshed from the directory it was
        made from; with it, that directory becomes the new origin. An entry
        registered by path before copies existed becomes a copy.

        Args:
            identifier: Qualified or short identifier.
            source: New directory holding ``copier.yml`` or ``copier.yaml``.

        Returns:
            TemplateEntry: The updated entry.

        Raises:
            ProjectServiceError: If unknown, not user-owned, or the origin is
                gone or invalid.
        """
        entry = self.resolve(identifier)
        if entry.origin is not TemplateOrigin.USER:
            raise ProjectServiceError(
                operation="update_template",
                reason=f"Official templates cannot be updated: {identifier}",
            )
        origin = source or entry.copied_from or entry.source
        if source is None and not origin.is_dir():
            raise ProjectServiceError(
                operation="update_template",
                reason=f"Template origin is gone: {origin}",
                details=f"Pass its new location: womm template update "
                f"{entry.id} SOURCE",
            )
        self._validate_source(origin, operation="update_template")
        updated = self._store_copy(entry.id, origin.expanduser().resolve())
        remaining = [item for item in self._load_user_entries() if item.id != entry.id]
        self._save_user_entries([*remaining, updated])
        return updated

    # ///////////////////////////////////////////////////////////
    # PRIVATE METHODS - DISCOVERY
    # ///////////////////////////////////////////////////////////

    def _discover_official(self) -> list[TemplateEntry]:
        """Enumerate shipped templates, without persisting anything."""
        root = Path(str(packaged_copier_official()))
        if not root.is_dir():
            return []
        entries: list[TemplateEntry] = []
        for candidate in sorted(root.iterdir()):
            manifest = _find_manifest(candidate)
            if manifest is None:
                continue
            metadata = self._read_metadata(manifest)
            setup = metadata.get("setup", {})
            setup = setup if isinstance(setup, dict) else {}
            entries.append(
                TemplateEntry(
                    id=candidate.name,
                    origin=TemplateOrigin.OFFICIAL,
                    source=candidate,
                    version=str(metadata.get("version", "")),
                    description=str(metadata.get("description", "")),
                    setup_language=str(setup.get("language", "")),
                )
            )
        return entries

    def _read_metadata(self, manifest: Path) -> dict[str, Any]:
        """Read the ``_womm`` block of a template manifest, tolerantly."""
        try:
            payload = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return {}
        block = payload.get(WOMM_METADATA_KEY, {})
        return block if isinstance(block, dict) else {}

    # ///////////////////////////////////////////////////////////
    # PRIVATE METHODS - CATALOG IO
    # ///////////////////////////////////////////////////////////

    def _load_user_entries(self) -> list[TemplateEntry]:
        """Read the user catalog, treating absence as empty.

        Metadata is read from each template's manifest; the stored copy of it
        only serves a missing source.
        """
        catalog = template_catalog_file()
        if not catalog.is_file():
            return []
        try:
            payload = json.loads(catalog.read_text(encoding="utf-8"))
            items = payload["templates"]
            return [
                replace(
                    self._build_user_entry(item["id"], Path(item["source"]))
                    if _find_manifest(Path(item["source"]))
                    else TemplateEntry(
                        id=item["id"],
                        origin=TemplateOrigin.USER,
                        source=Path(item["source"]),
                        version=item.get("version", ""),
                        description=item.get("description", ""),
                    ),
                    copied_from=Path(item["copied_from"])
                    if item.get("copied_from")
                    else None,
                )
                for item in items
            ]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ProjectServiceError(
                operation="load_catalog",
                reason=f"Template catalog is unreadable: {catalog}",
                details=str(exc),
            ) from exc

    def _save_user_entries(self, entries: list[TemplateEntry]) -> None:
        """Write the user catalog atomically."""
        catalog = template_catalog_file()
        user_templates_dir()
        payload = {
            "templates": [
                {
                    "id": entry.id,
                    "source": str(entry.source),
                    "copied_from": str(entry.copied_from)
                    if entry.copied_from
                    else None,
                    "version": entry.version,
                    "description": entry.description,
                }
                for entry in sorted(entries, key=lambda item: item.id)
            ]
        }
        handle, temp_name = tempfile.mkstemp(dir=str(catalog.parent), suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2)
            os.replace(temp_name, catalog)
        except OSError as exc:
            Path(temp_name).unlink(missing_ok=True)
            raise ProjectServiceError(
                operation="save_catalog",
                reason=f"Template catalog could not be written: {catalog}",
                details=str(exc),
            ) from exc

    # ///////////////////////////////////////////////////////////
    # PRIVATE METHODS - VALIDATION
    # ///////////////////////////////////////////////////////////

    def _validate_identifier(self, identifier: str, *, operation: str) -> None:
        """Accept ``name`` or ``namespace/name``; reject reserved namespaces.

        Each part names a directory of the copy, hence the strict charset.
        """
        if not identifier or identifier != identifier.strip():
            raise ProjectServiceError(
                operation=operation,
                reason="Template identifier must not be empty",
            )
        parts = identifier.split("/")
        if len(parts) > 2 or not all(
            IDENTIFIER_PART.fullmatch(part)
            and part.split(".")[0].upper() not in WINDOWS_RESERVED_NAMES
            for part in parts
        ):
            raise ProjectServiceError(
                operation=operation,
                reason=f"Template identifier must be name or namespace/name: "
                f"{identifier}",
                details="One namespace level at most; each part uses letters, "
                "digits, '.', '_' or '-', starts and ends with a letter or "
                "digit, and is not a reserved Windows name such as CON.",
            )
        if len(parts) == 2 and parts[0].lower() in RESERVED_NAMESPACES:
            raise ProjectServiceError(
                operation=operation,
                reason=f"Template namespace is reserved: {parts[0]}",
                details=f"{', '.join(sorted(RESERVED_NAMESPACES))} are reserved "
                "by WOMM.",
            )

    def _validate_source(self, source: Path, *, operation: str) -> None:
        """Reject remote sources and sources without a manifest."""
        raw = str(source)
        if raw.startswith(REMOTE_PREFIXES):
            raise ProjectServiceError(
                operation=operation,
                reason=f"Remote template sources are not supported yet: {raw}",
            )
        if _find_manifest(source.expanduser().resolve()) is None:
            raise ProjectServiceError(
                operation=operation,
                reason=f"Not a Copier template: {source}",
                details=f"Expected a {' or '.join(TEMPLATE_MANIFESTS)} file "
                "at the root.",
            )

    # ///////////////////////////////////////////////////////////
    # PRIVATE METHODS - COPIES
    # ///////////////////////////////////////////////////////////

    def _store_copy(self, identifier: str, origin: Path) -> TemplateEntry:
        """Copy ``origin`` into WOMM, replacing any previous copy only once
        the new one is complete.

        Returns:
            TemplateEntry: The entry rendered from the copy.
        """
        target = user_templates_dir() / COPIES_DIRNAME / Path(*identifier.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}-"))
        fresh, previous = staging / "fresh", staging / "previous"
        try:
            # A template's history is not part of it; symlinks stay links.
            shutil.copytree(
                origin, fresh, symlinks=True, ignore=shutil.ignore_patterns(".git")
            )
            if target.exists():
                target.rename(previous)
            fresh.rename(target)
        except OSError as exc:
            if previous.exists() and not target.exists():
                previous.rename(target)
            raise ProjectServiceError(
                operation="copy_template",
                reason=f"Template could not be copied into WOMM: {origin}",
                details=str(exc),
            ) from exc
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return replace(self._build_user_entry(identifier, target), copied_from=origin)

    def _is_copy(self, path: Path) -> bool:
        """Tell whether ``path`` is a copy WOMM owns, safe to delete."""
        copies = (user_templates_dir() / COPIES_DIRNAME).resolve()
        resolved = path.resolve()
        return resolved != copies and resolved.is_relative_to(copies)

    def _build_user_entry(self, identifier: str, source: Path) -> TemplateEntry:
        """Build a user entry, reading metadata from the manifest."""
        resolved = source.expanduser().resolve()
        manifest = _find_manifest(resolved)
        metadata = self._read_metadata(manifest) if manifest else {}
        setup = metadata.get("setup", {})
        setup = setup if isinstance(setup, dict) else {}
        return TemplateEntry(
            id=identifier,
            origin=TemplateOrigin.USER,
            source=resolved,
            version=str(metadata.get("version", "")),
            description=str(metadata.get("description", "")),
            setup_language=str(setup.get("language", "")),
        )


# ///////////////////////////////////////////////////////////////
# FUNCTIONS
# ///////////////////////////////////////////////////////////////


def _find_manifest(root: Path) -> Path | None:
    """Return the template manifest at ``root``, or ``None``."""
    return next(
        (root / name for name in TEMPLATE_MANIFESTS if (root / name).is_file()),
        None,
    )


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["TemplateStoreService"]
