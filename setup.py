#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# SETUP - Package Setup Script
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Setup script for works-on-my-machine package.
"""

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
from __future__ import annotations

import re
from pathlib import Path

from setuptools import setup

# ///////////////////////////////////////////////////////////////
# HELPERS
# ///////////////////////////////////////////////////////////////


def read_version() -> str:
    """Read project version from pyproject.toml [project] section.

    This avoids having to duplicate the version in multiple places.
    """
    pyproject_path = Path(__file__).with_name("pyproject.toml")
    content = pyproject_path.read_text(encoding="utf-8")

    in_project_section = False
    for line in content.splitlines():
        stripped = line.strip()

        if stripped.startswith("[project]"):
            in_project_section = True
            continue

        if (
            in_project_section
            and stripped.startswith("[")
            and not stripped.startswith("[project]")
        ):
            # We left the [project] section without finding a version
            break

        if in_project_section and stripped.startswith("version"):
            match = re.match(r'version\s*=\s*["\']([^"\']+)["\']', stripped)
            if match:
                return match.group(1)

    raise RuntimeError(  # noqa: TRY003
        "Unable to find [project].version in pyproject.toml"
    )


# ///////////////////////////////////////////////////////////////
# CONFIGURATION
# ///////////////////////////////////////////////////////////////

setup(
    name="works-on-my-machine",
    version=read_version(),
    description="Universal development tools for Python and JavaScript",
    author="Neuraaak",
    url="https://github.com/neuraaak/works-on-my-machine",
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
        "InquirerPy>=0.3.4",
        "tomli>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "womm=womm.cli:main",
        ],
    },
    packages=["womm"],
    include_package_data=True,
    zip_safe=False,
)
