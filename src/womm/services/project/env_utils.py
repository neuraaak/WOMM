#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# PROJECT ENV UTILS - Environment Setup Utilities
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Pure utility functions for setting up project environments.

This module provides stateless functions for:
- Python virtual environment creation and management
- npm project initialization
- Dependency installation (pip, npm)
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import logging
import shutil
import tomllib
import venv
from pathlib import Path

# Local imports
from ...shared.configs.project import PythonProjectConfig
from ...utils.project.validation_utils import validate_project_path
from ..common.command_runner_service import CommandRunnerService

# ///////////////////////////////////////////////////////////////
# LOGGER SETUP
# ///////////////////////////////////////////////////////////////

logger = logging.getLogger(__name__)

# ///////////////////////////////////////////////////////////////
# PYTHON ENVIRONMENT FUNCTIONS
# ///////////////////////////////////////////////////////////////


def get_virtual_environment_path(project_path: Path) -> Path:
    """Use the default environment, reusing a legacy environment when present."""
    default = project_path / PythonProjectConfig.VENV_DIR
    legacy = project_path / PythonProjectConfig.ALT_VENV_DIR
    return legacy if not default.exists() and legacy.is_dir() else default


def create_virtual_environment(
    project_path: Path, venv_name: str | None = None
) -> dict[str, str | bool]:
    """Create a Python virtual environment.

    Args:
        project_path: Path to the project
        venv_name: Venv directory name; defaults to .venv, reusing legacy venv.

    Returns:
        dict: Metadata with 'success', 'venv_path', and 'existing' keys

    Raises:
        ValueError: If validation fails
        OSError: If venv creation fails
    """
    validate_project_path(project_path, must_exist=True, require_empty=False)

    venv_path = (
        project_path / venv_name
        if venv_name
        else get_virtual_environment_path(project_path)
    )

    if venv_path.exists():
        logger.info(f"Virtual environment already exists at {venv_path}")
        return {
            "success": True,
            "venv_path": str(venv_path),
            "existing": True,
        }

    # Create virtual environment
    venv.create(venv_path, with_pip=True)
    logger.info(f"Created virtual environment at {venv_path}")

    # Upgrade pip
    _upgrade_pip(project_path, venv_path)

    return {
        "success": True,
        "venv_path": str(venv_path),
        "existing": False,
    }


def _upgrade_pip(project_path: Path, venv_path: Path) -> None:
    """Upgrade pip in the virtual environment.

    Args:
        project_path: Path to the project
        venv_path: Path to the virtual environment
    """
    try:
        # Find Python and pip executables
        python_exe = _find_venv_executable(venv_path, "python")
        pip_exe = _find_venv_executable(venv_path, "pip")

        if python_exe and pip_exe:
            command_runner = CommandRunnerService()
            result = command_runner.run(
                [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
                cwd=str(project_path),
            )
            if not result:  # Uses __bool__() which checks returncode == 0
                logger.warning(f"Failed to upgrade pip: {result.stderr}")
            else:
                logger.debug("Successfully upgraded pip")
    except Exception as e:
        logger.warning(f"Error upgrading pip: {e}")


def _find_venv_executable(venv_path: Path, name: str) -> Path | None:
    """Find an executable in the virtual environment.

    Args:
        venv_path: Path to the virtual environment
        name: Name of the executable (python, pip, etc.)

    Returns:
        Path | None: Path to the executable or None if not found
    """
    # Windows paths
    windows_paths = [
        venv_path / "Scripts" / f"{name}.exe",
        venv_path / "Scripts" / f"{name}3.exe",
    ]

    # Unix paths
    unix_paths = [
        venv_path / "bin" / name,
        venv_path / "bin" / f"{name}3",
    ]

    # Try Windows paths first (if drive exists, it's Windows)
    if venv_path.drive:
        for path in windows_paths:
            if path.exists():
                return path

    # Try Unix paths
    for path in unix_paths:
        if path.exists():
            return path

    return None


def find_pip_executable(venv_path: Path) -> Path:
    """Find pip executable in virtual environment.

    Args:
        venv_path: Path to the virtual environment

    Returns:
        Path: Path to pip executable

    Raises:
        FileNotFoundError: If pip executable not found
    """
    pip_exe = _find_venv_executable(venv_path, "pip")
    if not pip_exe:
        raise FileNotFoundError("pip not found in virtual environment")
    return pip_exe


def install_python_dependencies(
    project_path: Path, requirements_file: str = "requirements-dev.txt"
) -> bool:
    """Install Python dependencies from requirements file or pyproject.toml.

    Args:
        project_path: Path to the project
        requirements_file: Name of the requirements file

    Returns:
        bool: True if installation succeeded

    Raises:
        ValueError: If validation fails
        FileNotFoundError: If the virtual environment is missing
        RuntimeError: If the pip install command fails
    """
    validate_project_path(project_path, must_exist=True, require_empty=False)

    venv_path = get_virtual_environment_path(project_path)
    if not venv_path.exists():
        raise FileNotFoundError("Virtual environment not found")

    # Find pip executable
    pip_exe = find_pip_executable(venv_path)

    command_runner = CommandRunnerService()

    # Install dependencies from the legacy requirements file when available.
    req_file = project_path / requirements_file
    if req_file.exists():
        commands = [[str(pip_exe), "install", "-r", requirements_file]]
    else:
        pyproject_file = project_path / PythonProjectConfig.PYPROJECT_FILE
        if not pyproject_file.exists():
            logger.warning(f"Requirements file {requirements_file} not found, skipping")
            return True

        with pyproject_file.open("rb") as file:
            pyproject = tomllib.load(file)

        commands = []
        if "project" in pyproject:
            commands.append([str(pip_exe), "install", "."])
        if "dev" in pyproject.get("dependency-groups", {}):
            commands.append([str(pip_exe), "install", "--group", "dev"])

    for command in commands:
        result = command_runner.run(command, cwd=str(project_path))
        if not result:
            raise RuntimeError(f"Failed to install dependencies: {result.stderr}")

    if req_file.exists():
        logger.info(f"Successfully installed dependencies from {requirements_file}")
    else:
        logger.info("Successfully installed dependencies from pyproject.toml")
    return True


# ///////////////////////////////////////////////////////////////
# JAVASCRIPT ENVIRONMENT FUNCTIONS
# ///////////////////////////////////////////////////////////////


def check_npm_available() -> bool:
    """Check if npm is available in PATH.

    Returns:
        bool: True if npm is available
    """
    return shutil.which("npm") is not None


def install_npm_dependencies(project_path: Path) -> bool:
    """Install npm dependencies.

    Args:
        project_path: Path to the project

    Returns:
        bool: True if installation succeeded

    Raises:
        ValueError: If validation fails
        FileNotFoundError: If npm is not installed or not in PATH
        RuntimeError: If the npm install command fails
    """
    validate_project_path(project_path, must_exist=True, require_empty=False)

    if not check_npm_available():
        raise FileNotFoundError("npm is not installed or not in PATH")

    # Install dependencies
    command_runner = CommandRunnerService()
    result = command_runner.run(
        ["npm", "install"],
        cwd=str(project_path),
    )

    if not result:
        raise RuntimeError(f"Failed to install dependencies: {result.stderr}")

    logger.info("Successfully installed npm dependencies")
    return True


def install_npm_dev_dependencies(project_path: Path, dependencies: list[str]) -> bool:
    """Install npm development dependencies.

    Args:
        project_path: Path to the project
        dependencies: List of package names to install

    Returns:
        bool: True if installation succeeded

    Raises:
        ValueError: If validation fails
        FileNotFoundError: If npm is not installed or not in PATH
        RuntimeError: If the npm install command fails
    """
    validate_project_path(project_path, must_exist=True, require_empty=False)

    if not check_npm_available():
        raise FileNotFoundError("npm is not installed or not in PATH")

    if not dependencies:
        logger.info("No dev dependencies to install")
        return True

    # Install dev dependencies
    command_runner = CommandRunnerService()
    result = command_runner.run(
        ["npm", "install", "--save-dev", *dependencies],
        cwd=str(project_path),
    )

    if not result:
        raise RuntimeError(f"Failed to install development tools: {result.stderr}")

    logger.info(f"Successfully installed {len(dependencies)} dev dependencies")
    return True


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "check_npm_available",
    "create_virtual_environment",
    "find_pip_executable",
    "get_virtual_environment_path",
    "install_npm_dependencies",
    "install_npm_dev_dependencies",
    "install_python_dependencies",
]
