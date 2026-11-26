"""Display the concrete tooling plan before applying it."""

from rich.table import Table

from womm.shared.results.update_results import ToolingUpdateResult

from ...common import ezconsole, ezprinter


def print_tooling_update_plan(result: ToolingUpdateResult) -> None:
    """Show versions, file names and operations without configuration values."""
    table = Table(title="Tooling update", width=80)
    table.add_column("Tool")
    table.add_column("Current")
    table.add_column("Target")
    for tool, source, target in result.updates:
        table.add_row(tool, source, target)
    ezconsole.print(table)
    for operation in result.migrations:
        ezprinter.info(operation)
    if result.files:
        ezprinter.info("Files: " + ", ".join(result.files))
