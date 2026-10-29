#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEST LOGGING - Active WOMM Rich builders
# Project: Works On My Machine
# ///////////////////////////////////////////////////////////////

"""Tests for the active ``WommPrinter`` Rich builders."""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
from unittest.mock import MagicMock

# Third-party imports
import pytest
from ezplog import RichWizard
from rich.panel import Panel
from rich.table import Table

# Local imports
from womm.ui.common.logging import WommPrinter, ezprinter, ezwizard

# ///////////////////////////////////////////////////////////////
# FIXTURES
# ///////////////////////////////////////////////////////////////


@pytest.fixture
def printer():
    instance = WommPrinter()
    instance._console = MagicMock()
    return instance


# ///////////////////////////////////////////////////////////////
# INTEGRATION ADAPTERS
# ///////////////////////////////////////////////////////////////


def test_console_exposes_rich_console(printer):
    assert printer.console is printer._console


def test_logging_exports_public_rich_wizard():
    assert isinstance(ezwizard, RichWizard)
    assert ezprinter.console is not None


# ///////////////////////////////////////////////////////////////
# HEADER
# ///////////////////////////////////////////////////////////////


def test_print_header_prints_separators_and_title(printer):
    printer.print_header("My Title")

    assert printer._console.print.call_count == 4


# ///////////////////////////////////////////////////////////////
# PANEL BUILDERS
# ///////////////////////////////////////////////////////////////


def test_create_panel_returns_panel_with_given_content(printer):
    panel = printer.create_panel("body", title="T")

    assert isinstance(panel, Panel)


def test_create_info_panel_uses_info_icon(printer):
    panel = printer.create_info_panel("Info", "content")

    assert isinstance(panel, Panel)
    assert panel.title == "ℹ️ Info"


# ///////////////////////////////////////////////////////////////
# TABLE BUILDERS
# ///////////////////////////////////////////////////////////////


def test_create_table_with_simple_column_names(printer):
    table = printer.create_table("T", ["Name", "Value"], rows=[["a", "1"]])

    assert isinstance(table, Table)
    assert len(table.columns) == 2
    assert table.row_count == 1


def test_create_table_with_custom_column_tuples(printer):
    table = printer.create_table("T", [("Name", "cyan", True), ("Value", None, False)])

    assert len(table.columns) == 2


def test_create_backup_table_formats_all_rows(printer):
    table = printer.create_backup_table(
        [
            {
                "name": "a.json",
                "size": 500,
                "modified": "2026-01-01",
                "description": "x",
            },
            {
                "name": "b.json",
                "size": 2048,
                "modified": "2026-01-02",
                "description": "y" * 60,
            },
            {
                "name": "c.json",
                "size": 5 * 1024 * 1024,
                "modified": "2026-01-03",
                "description": "z",
            },
        ]
    )

    assert table.row_count == 3
