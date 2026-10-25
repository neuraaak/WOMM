#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# UI COMMON - Common UI Components
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Common UI components for Works On My Machine.

This module re-exports UI utilities, prompts, and interactive_menu.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Local imports
from .interactive_menu import InteractiveMenu, format_backup_item
from .logging import (
    DynamicLayeredProgress,
    WommPrinter,
    ezconsole,
    ezlogger,
    ezpl,
    ezprinter,
    ezwizard,
)
from .prompts import confirm, prompt_choice, prompt_path

# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////

__all__ = [
    "DynamicLayeredProgress",
    "WommPrinter",
    "InteractiveMenu",
    "confirm",
    "ezconsole",
    "ezlogger",
    "ezpl",
    "ezprinter",
    "ezwizard",
    "format_backup_item",
    "prompt_choice",
    "prompt_path",
]
