# ///////////////////////////////////////////////////////////////
# CONFTEST - Pytest configuration
# Project: Works On My Machine
# ///////////////////////////////////////////////////////////////

"""
Pytest configuration for Works On My Machine tests.

This module provides the session-wide data directory isolation and the pytest
hooks shared by the test suite.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import os
import shutil
import tempfile

# Third-party imports
import pytest

# ///////////////////////////////////////////////////////////////
# DATA DIRECTORY ISOLATION
# ///////////////////////////////////////////////////////////////

# Redirect the WOMM data directory onto a throwaway location for the whole
# session. This runs at *import* time, not in a fixture, on purpose: modules
# such as ``ui.common.logging`` resolve the log directory at import, which
# happens while pytest collects test modules — before any fixture could run.
# Without this, running the suite would write into the developer's real
# ``~/.womm``. ``setdefault`` leaves an explicit override in place.
_WOMM_HOME_ENV = "WOMM_HOME"
_TEST_WOMM_HOME = tempfile.mkdtemp(prefix="womm-test-home-")
os.environ.setdefault(_WOMM_HOME_ENV, _TEST_WOMM_HOME)

# ///////////////////////////////////////////////////////////////
# PYTEST HOOKS
# ///////////////////////////////////////////////////////////////


def pytest_configure(config: pytest.Config) -> None:
    """
    Configure pytest with custom markers.

    Args:
        config: Pytest configuration object
    """
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "robustness: mark test as a robustness test")
    config.addinivalue_line("markers", "security: mark test as a security test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "windows: mark test as Windows specific")
    config.addinivalue_line("markers", "linux: mark test as Linux specific")
    config.addinivalue_line("markers", "macos: mark test as macOS specific")


def pytest_sessionfinish(
    session: pytest.Session,  # noqa: ARG001
    exitstatus: int,  # noqa: ARG001
) -> None:
    """Remove the throwaway data directory created for the session.

    Args:
        session: Pytest session object (required by the hook signature)
        exitstatus: Session exit status (required by the hook signature)
    """
    shutil.rmtree(_TEST_WOMM_HOME, ignore_errors=True)


def pytest_collection_modifyitems(
    config: pytest.Config,  # noqa: ARG001
    items: list[pytest.Item],
) -> None:
    """
    Modify test collection to add markers based on test names.

    Args:
        config: Pytest configuration object (required by pytest hook signature)
        items: List of collected test items
    """
    for item in items:
        # Add unit marker to tests in unit directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add integration marker to tests in integration directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add robustness marker to tests in robustness directory
        if "robustness" in str(item.fspath):
            item.add_marker(pytest.mark.robustness)

        # Add security marker to security-related tests
        if "security" in item.name.lower():
            item.add_marker(pytest.mark.security)

        # Add slow marker to tests that might be slow
        if any(
            slow_indicator in item.name.lower()
            for slow_indicator in ["download", "install", "build", "deploy"]
        ):
            item.add_marker(pytest.mark.slow)
