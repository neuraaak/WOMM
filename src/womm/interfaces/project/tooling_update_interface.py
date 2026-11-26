"""Expose tooling updates through a stable result contract."""

from collections.abc import Callable
from pathlib import Path

import yaml

from womm.exceptions.project import ProjectServiceError
from womm.services.project.tooling_update_service import ToolingUpdateService
from womm.shared.results.update_results import ToolingUpdateResult


def update_tooling(
    project: Path,
    *,
    dry_run: bool,
    allow_destructive_actions: bool,
    approve: Callable[[ToolingUpdateResult], bool],
) -> ToolingUpdateResult:
    """Keep parser and filesystem diagnostics out of user configuration values."""
    try:
        return ToolingUpdateService().update(
            project,
            dry_run=dry_run,
            allow_destructive_actions=allow_destructive_actions,
            approve=approve,
        )
    except ProjectServiceError as exc:
        return ToolingUpdateResult(success=False, error=exc.reason)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        return ToolingUpdateResult(
            success=False,
            error="Cannot safely read or update this project's configuration; manual review is required",
        )
