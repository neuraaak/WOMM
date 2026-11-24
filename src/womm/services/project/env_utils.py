#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# PROJECT ENV UTILS - Environment Setup Utilities
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Pure utility functions for setting up project environments.

This module provides stateless functions for:
- Python virtual environment creation and management
- Dependency installation (pip or uv, and npm, pnpm, yarn or bun)
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import json
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
        python_exe = find_venv_executable(venv_path, "python")
        pip_exe = find_venv_executable(venv_path, "pip")

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


def find_venv_executable(venv_path: Path, name: str) -> Path | None:
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
    pip_exe = find_venv_executable(venv_path, "pip")
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


def uses_uv(project_path: Path) -> bool:
    """Tell whether a Python project is managed by uv.

    A freshly rendered uv project has no lockfile yet: the official template
    marks it with a ``[tool.uv]`` table instead.

    Args:
        project_path: Path to the project

    Returns:
        bool: True when the project has a ``uv.lock`` or a ``[tool.uv]`` table
    """
    if (project_path / "uv.lock").is_file():
        return True
    pyproject_file = project_path / PythonProjectConfig.PYPROJECT_FILE
    if not pyproject_file.is_file():
        return False
    try:
        with pyproject_file.open("rb") as file:
            pyproject = tomllib.load(file)
    except tomllib.TOMLDecodeError:
        return False
    return "uv" in pyproject.get("tool", {})


def sync_uv_environment(project_path: Path, install_deps: bool) -> None:
    """Create the project environment with uv, and install it on request.

    uv picks the interpreter from ``.python-version`` and ``requires-python``,
    and ``uv sync`` writes the ``uv.lock`` the generated CI requires.

    Args:
        project_path: Path to the project
        install_deps: Run ``uv sync --group dev`` instead of ``uv venv``

    Raises:
        FileNotFoundError: If uv is not on PATH
        RuntimeError: If the uv command fails
    """
    uv = shutil.which("uv")
    if not uv:
        raise FileNotFoundError(
            "uv is not installed or not on PATH; install uv, then run "
            "'uv sync' in the project"
        )

    command = (
        [uv, "sync", "--group", "dev"]
        if install_deps
        else [uv, "venv", "--allow-existing"]
    )
    result = CommandRunnerService().run(command, cwd=str(project_path))
    if not result:
        raise RuntimeError(f"uv {command[1]} failed: {result.stderr}")
    logger.info(f"Python environment ready with uv {command[1]}")


# ///////////////////////////////////////////////////////////////
# JAVASCRIPT ENVIRONMENT FUNCTIONS
# ///////////////////////////////////////////////////////////////


JAVASCRIPT_PACKAGE_MANAGERS = frozenset({"npm", "pnpm", "yarn", "bun"})

# Checked in order: a project carrying several lockfiles keeps the first match.
_JAVASCRIPT_LOCKFILES = (
    ("bun.lock", "bun"),
    ("bun.lockb", "bun"),
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("package-lock.json", "npm"),
)


def detect_package_manager(project_path: Path) -> str:
    """Return the package manager a JavaScript project uses.

    The ``packageManager`` field of ``package.json`` wins, then the lockfile;
    a project declaring neither uses npm.

    Args:
        project_path: Path to the project

    Returns:
        str: One of ``JAVASCRIPT_PACKAGE_MANAGERS``
    """
    try:
        manifest = json.loads((project_path / "package.json").read_text("utf-8"))
        declared = str(manifest.get("packageManager", "")).split("@", 1)[0]
    except (OSError, ValueError, AttributeError):
        declared = ""
    if declared in JAVASCRIPT_PACKAGE_MANAGERS:
        return declared

    for lockfile, manager in _JAVASCRIPT_LOCKFILES:
        if (project_path / lockfile).is_file():
            return manager
    return "npm"


def install_javascript_dependencies(project_path: Path) -> str:
    """Install the dependencies of a JavaScript project with its package manager.

    Args:
        project_path: Path to the project

    Returns:
        str: The package manager that installed the dependencies

    Raises:
        ValueError: If validation fails
        FileNotFoundError: If the package manager is not installed or not in PATH
        RuntimeError: If the install command fails
    """
    validate_project_path(project_path, must_exist=True, require_empty=False)

    manager = detect_package_manager(project_path)
    # Run the resolved path: npm, pnpm and yarn are .cmd shims on Windows.
    executable = shutil.which(manager)
    if executable is None:
        raise FileNotFoundError(f"{manager} is not installed or not in PATH")

    result = CommandRunnerService().run(
        [executable, "install"],
        cwd=str(project_path),
    )

    if not result:
        raise RuntimeError(f"{manager} install failed: {result.stderr}")

    logger.info(f"Successfully installed dependencies with {manager}")
    return manager


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "JAVASCRIPT_PACKAGE_MANAGERS",
    "create_virtual_environment",
    "detect_package_manager",
    "find_pip_executable",
    "find_venv_executable",
    "get_virtual_environment_path",
    "install_javascript_dependencies",
    "install_python_dependencies",
    "sync_uv_environment",
    "uses_uv",
]
