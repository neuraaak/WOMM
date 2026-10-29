#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEST SHARED CONFIGS FACADES - Remaining thin classmethod coverage
# Project: Works On My Machine
# ///////////////////////////////////////////////////////////////

"""
Tests for public configuration facades.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Local imports
from womm.shared.configs import ContextConfig
from womm.shared.configs.context import (
    ContextFileTypesConfig,
    ContextLimitsConfig,
    ContextPathsConfig,
)
from womm.shared.configs.project.python_project_config import PythonProjectConfig

# ///////////////////////////////////////////////////////////////
# PYTHON PROJECT CONFIG
# ///////////////////////////////////////////////////////////////


def test_get_dev_requirements_content_returns_template():
    assert (
        PythonProjectConfig.get_dev_requirements_content()
        == PythonProjectConfig.DEV_REQUIREMENTS_TEMPLATE
    )


def test_get_requirements_content_returns_template():
    assert (
        PythonProjectConfig.get_requirements_content()
        == PythonProjectConfig.REQUIREMENTS_TEMPLATE
    )


def test_format_dependency_joins_name_and_version():
    assert PythonProjectConfig.format_dependency("ruff", ">=0.5.0") == "ruff>=0.5.0"


def test_context_config_public_facade_keeps_specialized_values():
    assert ContextConfig.CONTEXT_PATHS is ContextPathsConfig.CONTEXT_PATHS
    assert (
        ContextConfig.REGISTRY_PATHS_BY_TYPE
        is ContextPathsConfig.REGISTRY_PATHS_BY_TYPE
    )
    assert ContextConfig.COMMAND_PARAMETERS is ContextPathsConfig.COMMAND_PARAMETERS
    assert (
        ContextConfig.FILE_TYPE_EXTENSIONS
        is ContextFileTypesConfig.FILE_TYPE_EXTENSIONS
    )
    assert (
        ContextConfig.VALID_SCRIPT_EXTENSIONS
        is ContextLimitsConfig.VALID_SCRIPT_EXTENSIONS
    )
    assert ContextConfig.MAX_PATH_LENGTH == ContextLimitsConfig.MAX_PATH_LENGTH
