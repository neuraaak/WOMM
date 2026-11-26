#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# UI - User Interface Module
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
User Interface module for Works On My Machine.

This package contains UI components using Rich for beautiful terminal output.
Provides console utilities, interactive components, and display functions.
"""

from __future__ import annotations

# Subpackages are not imported here: loading them all would make every
# `womm.ui.common` import (the CLI banner included) pay for the whole UI.

# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "common",
    "context",
    "project",
    "system",
]
