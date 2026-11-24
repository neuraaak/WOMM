#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# SERVICES PROJECT - Project Services
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Project services for Works On My Machine.

This package contains services for project management operations including
detection, validation, and configuration.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Local imports
from .detection_service import ProjectDetectionService
from .env_utils import (
    create_virtual_environment,
    find_pip_executable,
    install_javascript_dependencies,
    install_python_dependencies,
)
from .javascript_environment_service import JavaScriptEnvironmentService
from .python_environment_service import PythonEnvironmentService
from .validation_service import ProjectValidationService

# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "JavaScriptEnvironmentService",
    "ProjectDetectionService",
    "ProjectValidationService",
    "PythonEnvironmentService",
    "create_virtual_environment",
    "find_pip_executable",
    "install_javascript_dependencies",
    "install_python_dependencies",
]
