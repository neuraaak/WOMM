#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# PYTHON ENVIRONMENT SERVICE - Python Environment Setup Service
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Python Environment Service - Singleton service for Python environment setup.

Handles post-creation Python environment setup including:
- Virtual environment setup
- Dependency installation, development dependencies included
- Git repository initialization and pre-commit hooks installation
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import logging
from pathlib import Path
from threading import Lock
from typing import ClassVar

# Local imports
from ...exceptions.project import ProjectServiceError
from ...shared.configs.project import PythonProjectConfig
from ...shared.results import ProjectCreationResult
from ...utils.project import validate_project_path
from ..common.command_runner_service import CommandRunnerService
from .env_utils import (
    create_virtual_environment,
    find_venv_executable,
    get_virtual_environment_path,
    install_python_dependencies,
    sync_uv_environment,
)

# ///////////////////////////////////////////////////////////////
# LOGGER SETUP
# ///////////////////////////////////////////////////////////////

logger = logging.getLogger(__name__)

# ///////////////////////////////////////////////////////////////
# PYTHON ENVIRONMENT SERVICE CLASS
# ///////////////////////////////////////////////////////////////


class PythonEnvironmentService:
    """Singleton service for Python environment setup operations."""

    _instance: ClassVar[PythonEnvironmentService | None] = None
    _initialized: ClassVar[bool] = False
    _lock: ClassVar[Lock] = Lock()

    def __new__(cls) -> PythonEnvironmentService:
        """Create or return the singleton instance.

        Returns:
            PythonEnvironmentService: The singleton instance
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize Python environment service (only once)."""
        if PythonEnvironmentService._initialized:
            return

        self._command_runner = CommandRunnerService()
        self.logger = logging.getLogger(__name__)
        PythonEnvironmentService._initialized = True

    def setup_virtual_environment(self, project_path: Path) -> ProjectCreationResult:
        """Set up Python virtual environment.

        Args:
            project_path: Path to the project

        Returns:
            ProjectCreationResult: Result of venv setup

        Raises:
            ProjectServiceError: If venv setup fails
        """
        try:
            result = create_virtual_environment(project_path)
            if isinstance(result, dict) and result.get("success"):
                return ProjectCreationResult(
                    success=True,
                    message="Virtual environment created successfully",
                    project_path=project_path,
                    project_type="python",
                )
            else:
                raise ProjectServiceError(
                    operation="setup_virtual_environment",
                    reason="Virtual environment creation returned failure",
                )

        except ProjectServiceError:
            raise
        except Exception as e:
            logger.exception("Unexpected error in setup_virtual_environment")
            raise ProjectServiceError(
                operation="setup_virtual_environment",
                reason=str(e),
                details=f"Exception type: {type(e).__name__}",
            ) from e

    def install_dev_dependencies(self, project_path: Path) -> ProjectCreationResult:
        """Install development dependencies.

        Args:
            project_path: Path to the project

        Returns:
            ProjectCreationResult: Result of dependency installation

        Raises:
            ProjectServiceError: If dependency installation fails
        """
        try:
            success = install_python_dependencies(
                project_path, PythonProjectConfig.DEV_REQUIREMENTS_FILE
            )
            return ProjectCreationResult(
                success=success,
                message=(
                    "Development dependencies installed successfully"
                    if success
                    else "Failed to install development dependencies"
                ),
                project_path=project_path,
                project_type="python",
            )

        except ProjectServiceError:
            raise
        except Exception as e:
            logger.exception("Unexpected error in install_dev_dependencies")
            raise ProjectServiceError(
                operation="install_dev_dependencies",
                reason=str(e),
                details=f"Exception type: {type(e).__name__}",
            ) from e

    def setup_uv_environment(
        self, project_path: Path, install_deps: bool
    ) -> ProjectCreationResult:
        """Create the environment of a uv project, and install it on request.

        Args:
            project_path: Path to the project
            install_deps: Install the dependencies, dev group included

        Returns:
            ProjectCreationResult: Result of the uv run

        Raises:
            ProjectServiceError: If uv is missing or fails
        """
        try:
            sync_uv_environment(project_path, install_deps)
            return ProjectCreationResult(
                success=True,
                message="Python environment set up with uv",
                project_path=project_path,
                project_type="python",
            )

        except Exception as e:
            logger.exception("Unexpected error in setup_uv_environment")
            raise ProjectServiceError(
                operation="setup_uv_environment",
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

            # Check if git is available
            import shutil

            git_path = shutil.which("git")
            if not git_path:
                logger.info("Git not found, skipping repository initialization")
                return ProjectCreationResult(
                    success=True,
                    message="Git repository setup skipped (git not found)",
                    project_path=project_path,
                    project_type="python",
                    warnings=["Git not found in system PATH"],
                )

            # Initialize git repository
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
                    project_type="python",
                )
            else:
                logger.warning(f"Failed to initialize Git repository: {result.stderr}")
                return ProjectCreationResult(
                    success=False,
                    message="Failed to initialize Git repository",
                    project_path=project_path,
                    project_type="python",
                    error=result.stderr,
                )

        except ProjectServiceError:
            raise
        except Exception as e:
            logger.exception("Unexpected error in setup_git_repository")
            raise ProjectServiceError(
                operation="setup_git_repository",
                reason=str(e),
                details=f"Exception type: {type(e).__name__}",
            ) from e

    def install_git_hooks(self, project_path: Path) -> ProjectCreationResult:
        """Install the pre-commit hooks declared by the project.

        Runs the ``pre-commit`` of the project's virtual environment, so the
        hooks follow the version the project itself depends on.

        Args:
            project_path: Path to a project with a ``.pre-commit-config.yaml``

        Returns:
            ProjectCreationResult: Result of the hooks installation

        Raises:
            ProjectServiceError: If the installation raises unexpectedly
        """
        try:
            validate_project_path(project_path, must_exist=True, require_empty=False)

            if not (project_path / ".git").exists():
                return ProjectCreationResult(
                    success=False,
                    message="Git hooks need a Git repository",
                    project_path=project_path,
                    project_type="python",
                    error="no Git repository",
                )

            venv_path = get_virtual_environment_path(project_path)
            pre_commit = find_venv_executable(venv_path, "pre-commit")
            if pre_commit is None:
                return ProjectCreationResult(
                    success=False,
                    message="Git hooks not installed",
                    project_path=project_path,
                    project_type="python",
                    error=(
                        f"pre-commit is not installed in {venv_path.name}; "
                        "install the development dependencies first"
                    ),
                )

            result = self._command_runner.run(
                [str(pre_commit), "install"],
                description="Install pre-commit hooks",
                cwd=project_path,
            )
            if result.returncode == 0:
                return ProjectCreationResult(
                    success=True,
                    message="Git hooks installed successfully",
                    project_path=project_path,
                    project_type="python",
                )
            return ProjectCreationResult(
                success=False,
                message="Git hooks not installed",
                project_path=project_path,
                project_type="python",
                error=result.stderr or "pre-commit install failed",
            )

        except ProjectServiceError:
            raise
        except Exception as e:
            logger.exception("Unexpected error in install_git_hooks")
            raise ProjectServiceError(
                operation="install_git_hooks",
                reason=str(e),
                details=f"Exception type: {type(e).__name__}",
            ) from e


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = ["PythonEnvironmentService"]
