#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# PROJECT MANAGER - Project Creation and Management
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Main project manager for WOMM CLI.

Orchestrates project creation and management operations.
Provides unified interface for creating and managing projects
across different languages and frameworks.

This interface never raises: every public method returns a typed Result.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import logging
from pathlib import Path

# Local imports
from ...shared.results import (
    ProjectDetectionResult,
    ProjectSetupResult,
)
from .detection_interface import ProjectDetectionInterface
from .setup_interface import ProjectSetupInterface

# ///////////////////////////////////////////////////////////////
# MAIN CLASS
# ///////////////////////////////////////////////////////////////


class ProjectManagerInterface:
    """Main project manager for WOMM CLI."""

    def __init__(self):
        """Initialize the project manager."""
        self._setup_interface = ProjectSetupInterface()
        self._detection_interface = ProjectDetectionInterface()
        self.logger = logging.getLogger(__name__)

    # ///////////////////////////////////////////////////////////////
    # PUBLIC METHODS
    # ///////////////////////////////////////////////////////////////

    def detect_project_type(
        self, project_path: Path | None = None
    ) -> ProjectDetectionResult:
        """
        Detect the type of project in the given path.

        Args:
            project_path: Path to analyze (defaults to current directory)

        Returns:
            ProjectDetectionResult: Detection result with project type and confidence
        """
        return self._detection_interface.detect_project_type(project_path)

    def setup_project(
        self,
        project_type: str,
        project_path: Path,
        virtual_env: bool = False,
        install_deps: bool = False,
        setup_git_hooks: bool = False,
        **kwargs,
    ) -> ProjectSetupResult:
        """
        Set up an existing project with development tools and configuration.

        Args:
            project_type: Type of project (python, javascript, react, vue)
            project_path: Path to the existing project
            virtual_env: Whether to create virtual environment (Python only)
            install_deps: Whether to install dependencies
            setup_git_hooks: Whether to set up Git hooks
            **kwargs: Additional project-specific options

        Returns:
            ProjectSetupResult: Result of the setup operation
        """
        return self._setup_interface.setup_project(
            project_path=project_path,
            project_type=project_type,
            virtual_env=virtual_env,
            install_deps=install_deps,
            setup_git_hooks=setup_git_hooks,
            **kwargs,
        )
