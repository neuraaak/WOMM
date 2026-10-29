#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# ASSET UTILS - Asset Path Resolution and Copying
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Pure utility functions for asset management.

This module provides stateless functions for:
- Copying individual asset files
- Copying asset directories recursively
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import logging
import shutil
from pathlib import Path

# ///////////////////////////////////////////////////////////////
# LOGGER SETUP
# ///////////////////////////////////////////////////////////////

logger = logging.getLogger(__name__)

# ///////////////////////////////////////////////////////////////
# ASSET FILE OPERATIONS
# ///////////////////////////////////////////////////////////////


def copy_asset_file(
    source: Path,
    target: Path,
    overwrite: bool = False,
    create_parents: bool = True,
) -> Path:
    """Copy a single asset file to target location.

    Args:
        source: Source file path
        target: Target file path
        overwrite: If True, overwrite existing files. If False, skip if exists.
        create_parents: If True, create parent directories if they don't exist

    Returns:
        Path: Path to the copied file (or existing file if skipped)

    Raises:
        FileNotFoundError: If the source file does not exist
        IsADirectoryError: If the source path is not a file
        OSError: If the copy operation fails
    """
    # Validate source
    if not source.exists():
        raise FileNotFoundError(f"Source file does not exist: {source}")

    if not source.is_file():
        raise IsADirectoryError(f"Source path is not a file: {source}")

    # Check if target exists
    if target.exists() and not overwrite:
        logger.debug(f"Skipping {target} (already exists, overwrite=False)")
        return target

    # Create parent directories if needed
    if create_parents:
        target.parent.mkdir(parents=True, exist_ok=True)

    # Copy the file
    shutil.copy2(source, target)
    logger.debug(f"Copied {source} to {target}")

    return target


def copy_assets_directory(
    source: Path,
    target: Path,
    overwrite: bool = False,
    exclude_patterns: list[str] | None = None,
) -> list[Path]:
    """Copy an asset directory recursively to target location.

    Args:
        source: Source directory path
        target: Target directory path
        overwrite: If True, overwrite existing files. If False, skip if exists.
        exclude_patterns: Optional list of glob patterns to exclude

    Returns:
        list[Path]: List of copied file paths (relative to target)

    Raises:
        FileNotFoundError: If the source directory does not exist
        NotADirectoryError: If the source path is not a directory
        OSError: If the copy operation fails
    """
    # Validate source
    if not source.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source}")

    if not source.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source}")

    copied_files = []
    exclude_patterns = exclude_patterns or []

    # Create target directory
    target.mkdir(parents=True, exist_ok=True)

    # Copy files recursively
    for item in source.rglob("*"):
        if item.is_file():
            # Check exclude patterns
            relative_path = item.relative_to(source)
            if any(relative_path.match(pattern) for pattern in exclude_patterns):
                logger.debug(f"Excluding {relative_path} (matches pattern)")
                continue

            # Determine target file path
            target_file = target / relative_path

            # Skip if exists and overwrite is False
            if target_file.exists() and not overwrite:
                logger.debug(
                    f"Skipping {target_file} (already exists, overwrite=False)"
                )
                continue

            # Create parent directories
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file
            shutil.copy2(item, target_file)
            copied_files.append(target_file)
            logger.debug(f"Copied {item} to {target_file}")

    logger.info(f"Copied {len(copied_files)} files from {source} to {target}")
    return copied_files


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "copy_asset_file",
    "copy_assets_directory",
]
