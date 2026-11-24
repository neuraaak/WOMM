#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# JAVASCRIPT ENVIRONMENT SERVICE - JavaScript Environment Setup Service
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
JavaScript Environment Service - Singleton service for JavaScript environment setup.

Handles post-creation JavaScript/Node.js/React/Vue environment setup:
- Dependency installation with the project's package manager
- Git repository initialization

Development tools are the project's own devDependencies: WOMM installs them
and never adds a linter, formatter or hook manager of its own.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import logging
import shutil
from pathlib import Path
from threading import Lock
from typing import ClassVar

# Local imports
from ...exceptions.project import ProjectServiceError
from ...shared.results import ProjectCreationResult
from ...utils.project import validate_project_path
from ..common.command_runner_service import CommandRunnerService
from .env_utils import install_javascript_dependencies

# ///////////////////////////////////////////////////////////////
# LOGGER SETUP
# ///////////////////////////////////////////////////////////////

logger = logging.getLogger(__name__)

# ///////////////////////////////////////////////////////////////
# CONSTANTS
# ///////////////////////////////////////////////////////////////

JAVASCRIPT_PROJECT_TYPES = frozenset({"javascript", "node", "react", "vue"})


def _validate_javascript_project_type(project_type: str) -> None:
    """Validate a JavaScript service project type."""
    if project_type not in JAVASCRIPT_PROJECT_TYPES:
        supported_types = ", ".join(sorted(JAVASCRIPT_PROJECT_TYPES))
        raise ValueError(
            f"Unsupported JavaScript project type: {project_type}. "
            f"Supported types: {supported_types}"
        )


# ///////////////////////////////////////////////////////////////
# JAVASCRIPT ENVIRONMENT SERVICE CLASS
# ///////////////////////////////////////////////////////////////


class JavaScriptEnvironmentService:
    """Singleton service for JavaScript environment setup operations."""

    _instance: ClassVar[JavaScriptEnvironmentService | None] = None
    _initialized: ClassVar[bool] = False
    _lock: ClassVar[Lock] = Lock()

    def __new__(cls) -> JavaScriptEnvironmentService:
        """Create or return the singleton instance.

        Returns:
            JavaScriptEnvironmentService: The singleton instance
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize JavaScript environment service (only once)."""
        if JavaScriptEnvironmentService._initialized:
            return

        self._command_runner = CommandRunnerService()
        self.logger = logging.getLogger(__name__)
        JavaScriptEnvironmentService._initialized = True

    def install_dependencies(
        self,
        project_path: Path,
        project_type: str,
    ) -> ProjectCreationResult:
        """Install project dependencies.

        Args:
            project_path: Path to the project
            project_type: Type of JavaScript project (node, react, vue)

        Returns:
            ProjectCreationResult: Result of dependency installation

        Raises:
            ProjectServiceError: If dependency installation fails
        """
        try:
            validate_project_path(project_path, must_exist=True, require_empty=False)
            _validate_javascript_project_type(project_type)

            manager = install_javascript_dependencies(project_path)

            return ProjectCreationResult(
                success=True,
                message=f"Dependencies installed with {manager}",
                project_path=project_path,
                project_type=project_type,
            )

        except ProjectServiceError:
            raise
        except Exception as e:
            logger.exception("install_dependencies failed")
            raise ProjectServiceError(
                operation="install_dependencies",
                reason=str(e),
                details=f"Exception type: {type(e).__name__}",
            ) from e

    def setup_git_repository(self, project_path: Path) -> ProjectCreationResult:
        """Initialize a Git repository for the project.

        Args:
            project_path: Path to the project

        Returns:
            ProjectCreationResult: Result of Git setup

        Raises:
            ProjectServiceError: If Git setup fails
        """
        try:
            validate_project_path(project_path, must_exist=True, require_empty=False)

            # Initialize git repository using CommandRunnerService
            git_path = shutil.which("git")
            if not git_path:
                logger.info("Git not found, skipping repository initialization")
                return ProjectCreationResult(
                    success=True,
                    message="Git repository setup skipped (git not found)",
                    project_path=project_path,
                    warnings=["Git not found in system PATH"],
                )
            result = self._command_runner.run(
                [git_path, "init"],
                description="Initialize Git repository",
                cwd=project_path,
            )

            if result.returncode == 0:
                return ProjectCreationResult(
                    success=True,
                    message="Git repository initialized successfully",
                    project_path=project_path,
                )
            else:
                logger.warning(f"Failed to initialize Git repository: {result.stderr}")
                return ProjectCreationResult(
                    success=False,
                    message="Failed to initialize Git repository",
                    project_path=project_path,
                    error=result.stderr,
                )

        except ProjectServiceError:
            raise
        except Exception as e:
            raise ProjectServiceError(
                operation="setup_git_repository",
                reason=str(e),
                details=f"Exception type: {type(e).__name__}",
            ) from e


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["JavaScriptEnvironmentService"]
