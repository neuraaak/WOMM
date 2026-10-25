#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEST SHARED CONFIGS FACADES - Remaining thin classmethod coverage
# Project: Works On My Machine
# ///////////////////////////////////////////////////////////////

"""
Tests for ``PythonProjectConfig``'s static formatters.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Local imports
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
