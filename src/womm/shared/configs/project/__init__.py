#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# PROJECT CONFIGS - Project Configuration Modules
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Project configuration modules for Works On My Machine.

This package contains configuration classes for:
- Project structure
- Project types (Python, JavaScript)
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Local imports
from .project_config import ProjectConfig
from .project_structure_config import ProjectStructureConfig
from .python_project_config import PythonProjectConfig

# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "ProjectConfig",
    "ProjectStructureConfig",
    "PythonProjectConfig",
]
