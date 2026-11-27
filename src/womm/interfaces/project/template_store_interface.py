#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEMPLATE STORE INTERFACE - Template Catalog Interface
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Template store interface for WOMM CLI.

Orchestrates catalog operations (list, show, add, remove, update) against
``TemplateStoreService`` and template scaffolding against
``CopierProjectCreationService``. This interface never raises: service
exceptions are converted into a typed Result.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path

# Local imports
from ...exceptions.project import ProjectServiceError
from ...services.project.copier_project_creation_service import (
    CopierProjectCreationService,
    ProjectCreationRequest,
)
from ...services.project.template_extraction_service import (
    TemplateExtractionService,
)
from ...services.project.template_store_service import TemplateStoreService
from ...shared.paths import packaged_copier_meta
from ...shared.results.template_results import (
    TemplateInitResult,
    TemplateListResult,
    TemplateStoreResult,
)

# Meta-template questions reserved to ``init_template(source=...)``.
EXTRACTION_FLAGS = ("extracted", "has_identity", "has_package")

# ///////////////////////////////////////////////////////////////
# MAIN CLASS
# ///////////////////////////////////////////////////////////////


class TemplateStoreInterface:
    """Orchestrate catalog operations and template scaffolding."""

    def __init__(self) -> None:
        """Initialize the template store interface."""
        self._store = TemplateStoreService()
        self._creator = CopierProjectCreationService()
        self._extractor = TemplateExtractionService()

    # ///////////////////////////////////////////////////////////////
    # PUBLIC METHODS
    # ///////////////////////////////////////////////////////////////

    def list_templates(self) -> TemplateListResult:
        """List every known template.

        Returns:
            TemplateListResult: Typed outcome, never raises.
        """
        try:
            entries = self._store.list_templates()
        except ProjectServiceError as exc:
            return TemplateListResult(success=False, error=str(exc))
        return TemplateListResult(
            success=True,
            message=f"{len(entries)} template(s) available",
            entries=entries,
        )

    def show_template(self, identifier: str) -> TemplateStoreResult:
        """Show a single catalog entry.

        Args:
            identifier: Qualified or short template identifier.

        Returns:
            TemplateStoreResult: Typed outcome, never raises.
        """
        try:
            entry = self._store.resolve(identifier)
        except ProjectServiceError as exc:
            return TemplateStoreResult(success=False, error=str(exc))
        return TemplateStoreResult(
            success=True,
            message=f"Template found: {entry.qualified_id}",
            entry=entry,
        )

    def preview_template(self, identifier: str, source: Path) -> TemplateStoreResult:
        """Show the entry ``add_template`` would register, without writing.

        Args:
            identifier: Short identifier, without any separator.
            source: Directory holding ``copier.yml`` or ``copier.yaml``.

        Returns:
            TemplateStoreResult: Typed outcome, never raises.
        """
        try:
            entry = self._store.preview(identifier, source)
        except ProjectServiceError as exc:
            return TemplateStoreResult(success=False, error=str(exc))
        return TemplateStoreResult(
            success=True,
            message=f"Template to register: {entry.qualified_id}",
            entry=entry,
        )

    def add_template(self, identifier: str, source: Path) -> TemplateStoreResult:
        """Register a local template under the user namespace.

        Args:
            identifier: Short identifier, without any separator.
            source: Directory holding ``copier.yml``.

        Returns:
            TemplateStoreResult: Typed outcome, never raises.
        """
        try:
            entry = self._store.add(identifier, source)
        except ProjectServiceError as exc:
            return TemplateStoreResult(success=False, error=str(exc))
        return TemplateStoreResult(
            success=True,
            message=f"Template registered: {entry.qualified_id}",
            entry=entry,
        )

    def remove_template(self, identifier: str) -> TemplateStoreResult:
        """Unregister a user template.

        Args:
            identifier: Qualified or short identifier.

        Returns:
            TemplateStoreResult: Typed outcome, never raises.
        """
        try:
            entry = self._store.remove(identifier)
        except ProjectServiceError as exc:
            return TemplateStoreResult(success=False, error=str(exc))
        return TemplateStoreResult(
            success=True,
            message=f"Template removed: {entry.qualified_id}",
            entry=entry,
        )

    def update_template(
        self, identifier: str, source: Path | None = None
    ) -> TemplateStoreResult:
        """Refresh WOMM's copy of a user template, from a new source if given.

        Args:
            identifier: Qualified or short identifier.
            source: New directory holding ``copier.yml``; ``None`` refreshes
                from the directory the copy was made from.

        Returns:
            TemplateStoreResult: Typed outcome, never raises.
        """
        try:
            entry = self._store.update(identifier, source)
        except ProjectServiceError as exc:
            return TemplateStoreResult(success=False, error=str(exc))
        return TemplateStoreResult(
            success=True,
            message=f"Template updated: {entry.qualified_id}",
            entry=entry,
        )

    def init_template(
        self,
        destination: Path,
        *,
        answers: Mapping[str, str],
        force: bool = False,
        defaults: bool = False,
        source: Path | None = None,
        excludes: Sequence[str] = (),
    ) -> TemplateInitResult:
        """Scaffold a new Copier template skeleton.

        The skeleton is rendered by the same service as projects: WOMM has no
        second rendering engine. Without ``source`` it carries no inference.
        With ``source``, the template content is a snapshot of that git
        project whose own names become variables; the whole extraction is
        checked before anything is written.

        Args:
            destination: Directory to scaffold into.
            answers: Pre-filled meta-template answers.
            force: Allow a non-empty destination.
            defaults: Use defaults instead of prompting.
            source: Root of a git project to extract the template from.
            excludes: Patterns of tracked files to leave out of the snapshot.

        Returns:
            TemplateInitResult: Typed outcome, never raises.
        """
        existed = destination.exists()
        # Only an extraction may set the internal meta-template flags.
        answers = {**answers, **dict.fromkeys(EXTRACTION_FLAGS, "false")}
        try:
            plan = None
            if source is not None:
                plan = self._extractor.plan(source, destination, excludes)
                answers = {**answers, "extracted": "true", **plan.meta_answers}
            warnings = self._creator.create(
                ProjectCreationRequest(
                    template_source=Path(str(packaged_copier_meta())),
                    destination=destination,
                    answers=dict(answers),
                    force=force,
                    defaults=defaults,
                )
            )
            if plan is not None:
                try:
                    self._extractor.write(plan, destination / "template")
                except OSError:
                    # Never leave a half-written template where there was none.
                    if not existed:
                        shutil.rmtree(destination, ignore_errors=True)
                    raise
        except (ProjectServiceError, OSError) as exc:
            return TemplateInitResult(
                success=False, error=str(exc), project_path=destination
            )
        return TemplateInitResult(
            success=True,
            message=f"Template skeleton created at {destination}",
            project_path=destination,
            project_name=destination.name,
            warnings=warnings or None,
            extraction=plan.report if plan is not None else None,
        )


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["TemplateStoreInterface"]
