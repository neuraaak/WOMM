#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# COPIER PROJECT CREATION SERVICE - Copier-backed rendering
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Project rendering, delegated to Copier.

Copier owns the questionnaire and the rendering. WOMM owns the destination
contract, the security posture (no tasks, no unsafe features) and the
translation of Copier failures into ``ProjectServiceError``.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from womm._version import __version__
from womm.exceptions.project import ProjectServiceError

from .destination_guard import check_destination

# ///////////////////////////////////////////////////////////////
# REQUEST
# ///////////////////////////////////////////////////////////////


@dataclass(frozen=True)
class ProjectCreationRequest:
    """Everything needed to render one project.

    Attributes:
        template_source: Path to the template root holding ``copier.yml``.
        destination: Directory to render into.
        answers: Pre-filled answers, keyed by Copier question name.
        force: Allow rendering into a non-empty destination.
        pretend: Simulate the rendering without writing anything.
        defaults: Use declared defaults instead of prompting.
    """

    template_source: Path
    destination: Path
    answers: Mapping[str, object] = field(default_factory=dict)
    force: bool = False
    pretend: bool = False
    defaults: bool = False


# ///////////////////////////////////////////////////////////////
# SERVICE
# ///////////////////////////////////////////////////////////////


class CopierProjectCreationService:
    """Render a project from a Copier template."""

    def create(self, request: ProjectCreationRequest) -> list[str]:
        """Render a template into its destination.

        A simulation never touches the filesystem, so it bypasses the
        destination guard: simulating against an existing project must stay
        possible.

        A template that is a local git repository is rendered from its working
        copy (``HEAD`` plus uncommitted changes), never from its latest tag.

        Args:
            request: Immutable rendering request.

        Returns:
            list[str]: Warnings to surface, empty when there are none.

        Raises:
            ProjectServiceError: If the destination is refused or Copier fails.
        """
        # Copier costs ~600 ms to import: only the command that renders pays it.
        import copier
        from copier.errors import DirtyLocalWarning

        if not request.pretend:
            check_destination(request.destination, force=request.force)

        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", DirtyLocalWarning)
                copier.run_copy(
                    src_path=str(request.template_source),
                    dst_path=str(request.destination),
                    data={**request.answers, "_womm_version": __version__},
                    # Without it, Copier renders a git template's latest tag.
                    vcs_ref="HEAD",
                    overwrite=request.force,
                    pretend=request.pretend,
                    defaults=request.defaults,
                    cleanup_on_error=True,
                    unsafe=False,
                    skip_tasks=True,
                    quiet=True,
                )
        except ProjectServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 - Copier raises many types
            raise ProjectServiceError(
                operation="create_project",
                reason=f"Template rendering failed: {request.template_source}",
                details=str(exc),
            ) from exc

        result: list[str] = []
        for caught_warning in caught:
            if issubclass(caught_warning.category, DirtyLocalWarning):
                result.append(
                    f"Uncommitted changes in {request.template_source} were "
                    "included in the rendering"
                )
            else:
                warnings.warn_explicit(
                    caught_warning.message,
                    caught_warning.category,
                    caught_warning.filename,
                    caught_warning.lineno,
                )
        return result


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["CopierProjectCreationService", "ProjectCreationRequest"]
