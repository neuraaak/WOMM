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

import os

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath

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
from ...services.project.template_update_service import TemplateUpdateService
from ...shared.models.template_source import TemplateEntry, TemplateOrigin
from ...shared.paths import packaged_copier_meta
from ...shared.results.template_results import (
    TemplateInitResult,
    TemplateListResult,
    TemplateStoreResult,
    TemplateUpdatePreview,
    TemplateUpdateResult,
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
        self._updater = TemplateUpdateService()

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

    def plan_update(
        self,
        target: str,
        source: Path | None = None,
        project: Path | None = None,
    ) -> TemplateUpdatePreview:
        """Work out what ``template update TARGET`` would do, writing nothing.

        TARGET is a path when written as one (``./x``, ``../x``, ``~/x`` or
        absolute), else a catalog identifier, else an existing directory.

        Args:
            target: Template identifier or template directory.
            source: With an identifier, the template's new directory.
            project: Project to extract from instead of the trace's origin.

        Returns:
            TemplateUpdatePreview: Typed outcome, never raises.
        """
        try:
            template, entry, others = self._resolve_update_target(target, source)
            plan = None
            if template is not None and (
                project is not None or self._updater.has_trace(template)
            ):
                plan = self._updater.plan(template, project)
            elif entry is None:
                raise ProjectServiceError(
                    operation="update_template",
                    reason=f"Nothing to update: {target}",
                    details="It has no extraction trace and is not registered.",
                )
            elif project is not None:
                raise ProjectServiceError(
                    operation="update_template",
                    reason=f"--from needs the template's own directory: {target}",
                    details="Pass it as SOURCE, or update the template by its path.",
                )
        except (ProjectServiceError, OSError) as exc:
            return TemplateUpdatePreview(success=False, error=str(exc))
        return TemplateUpdatePreview(
            success=True,
            template=template,
            entry=entry,
            other_ids=others,
            changes=plan.changes if plan else [],
            unchanged=plan.unchanged if plan else 0,
            kept=plan.kept if plan else 0,
            report=plan.report if plan else None,
            plan=(plan, source),
        )

    def apply_update(
        self,
        preview: TemplateUpdatePreview,
        decisions: Mapping[PurePosixPath, bool],
        *,
        publish: bool = True,
    ) -> TemplateUpdateResult:
        """Apply a previewed update, then refresh the store when asked.

        Args:
            preview: Successful result of :meth:`plan_update`.
            decisions: Answer to each question, keyed by project path; a
                missing answer leaves the question pending.
            publish: Whether to refresh the catalog entry's copy.

        Returns:
            TemplateUpdateResult: Typed outcome, never raises. A store failure
            after the template was updated is reported in ``store_error``.
        """
        plan, source = preview.plan
        try:
            outcome = self._updater.apply(plan, decisions) if plan else None
        except (ProjectServiceError, OSError) as exc:
            return TemplateUpdateResult(success=False, error=str(exc))
        entry = None
        store_error = ""
        if publish and preview.entry is not None:
            try:
                entry = self._store.update(preview.entry.id, source)
            except (ProjectServiceError, OSError) as exc:
                store_error = str(exc)
        if outcome is None and store_error:
            return TemplateUpdateResult(success=False, error=store_error)
        return TemplateUpdateResult(
            success=True,
            message="Template updated" if outcome else "Store refreshed",
            outcome=outcome,
            entry=entry,
            store_error=store_error,
        )

    def _resolve_update_target(
        self, target: str, source: Path | None
    ) -> tuple[Path | None, TemplateEntry | None, list[str]]:
        """Template directory, associated entry and other candidates of TARGET."""
        explicit = (
            target.startswith((".", "~"))
            or os.path.isabs(target)
            or Path(target).drive != ""
        )
        if not explicit:
            try:
                entry = self._store.resolve(target)
            except ProjectServiceError:
                if not Path(target).is_dir():
                    raise
            else:
                if entry.origin is not TemplateOrigin.USER:
                    raise ProjectServiceError(
                        operation="update_template",
                        reason=f"Official templates cannot be updated: {target}",
                    )
                origin = source or entry.copied_from or entry.source
                template = origin.expanduser().resolve()
                if self._store.is_stored(template):
                    if source is not None:
                        raise _stored_copy_refused(template)
                    return None, entry, []  # only WOMM's copy is known
                return template, entry, []
        if source is not None:
            raise ProjectServiceError(
                operation="update_template",
                reason="SOURCE only goes with a template identifier",
            )
        template = Path(target).expanduser().resolve()
        if self._store.is_stored(template):
            raise _stored_copy_refused(template)
        linked = [
            e
            for e in self._store.list_templates()
            if e.copied_from is not None and e.copied_from.resolve() == template
        ]
        if len(linked) == 1:
            return template, linked[0], []
        return template, None, sorted(e.id for e in linked)

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
                    self._extractor.write(plan)
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


def _stored_copy_refused(path: Path) -> ProjectServiceError:
    # Versions in WOMM's store are archives: they are never changed in place.
    return ProjectServiceError(
        operation="update_template",
        reason=f"WOMM's own copies cannot be updated in place: {path}",
        details="Update the template's original directory instead.",
    )


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["TemplateStoreInterface"]
