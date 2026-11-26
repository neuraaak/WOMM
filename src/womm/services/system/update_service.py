#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# UPDATE SERVICE - PyPI Release Check
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""
Tell whether a newer WOMM release is published on PyPI.

The answer is cached in the data directory for a day, so at most one command
a day pays for the network call. Every failure (offline, timeout, unexpected
answer, unwritable cache) means "no update known": a release check must never
break or slow down the command it rides on.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library imports
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Local imports
from ...shared.paths import update_check_file

# ///////////////////////////////////////////////////////////////
# CONSTANTS
# ///////////////////////////////////////////////////////////////

PACKAGE_NAME = "womm-cli"
_PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
_MAX_AGE_SECONDS = 24 * 60 * 60
_TIMEOUT_SECONDS = 1.0
# The PyPI answer grows with the release count; a few hundred KB at most.
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
# Final releases only: a pre-release is never offered as an update.
_RELEASE_PATTERN = re.compile(r"\d+(\.\d+)*")

# ///////////////////////////////////////////////////////////////
# RESULT TYPE
# ///////////////////////////////////////////////////////////////


@dataclass(frozen=True)
class UpdateInfo:
    """A newer release than the installed one."""

    current: str
    latest: str
    upgrade_command: str


# ///////////////////////////////////////////////////////////////
# PUBLIC API
# ///////////////////////////////////////////////////////////////


def is_newer(candidate: str, current: str) -> bool:
    """Tell whether ``candidate`` is a final release above ``current``.

    Args:
        candidate: Version published on PyPI.
        current: Installed version.

    Returns:
        bool: False as soon as either version is not a plain ``X.Y.Z``.
    """
    if not (
        _RELEASE_PATTERN.fullmatch(candidate) and _RELEASE_PATTERN.fullmatch(current)
    ):
        return False
    return _as_tuple(candidate) > _as_tuple(current)


def upgrade_command() -> str:
    """Return the command that upgrades the running installation."""
    parts = {part.lower() for part in Path(sys.prefix).parts}
    if "uv" in parts and "tools" in parts:
        return f"uv tool upgrade {PACKAGE_NAME}"
    if "pipx" in parts:
        return f"pipx upgrade {PACKAGE_NAME}"
    return f"python -m pip install --upgrade {PACKAGE_NAME}"


def latest_release(*, now: float | None = None) -> str | None:
    """Return the latest release on PyPI, refreshing the cache once a day.

    Args:
        now: Current time, as ``time.time()``; injectable for tests.

    Returns:
        str | None: The latest known release, or None when PyPI has never
        been reached.
    """
    now = time.time() if now is None else now
    cache = _read_cache()
    latest = cache.get("latest")
    latest = latest if isinstance(latest, str) else None
    checked_at = cache.get("checked_at")

    fresh = (
        isinstance(checked_at, int | float) and 0 <= now - checked_at < _MAX_AGE_SECONDS
    )
    if not fresh:
        # A failed fetch keeps the last known release and still stamps the
        # check, so an offline machine does not retry on every command.
        latest = _fetch_latest() or latest
        _write_cache({"checked_at": now, "latest": latest})
    return latest


def check_for_update(current: str, *, now: float | None = None) -> UpdateInfo | None:
    """Return the newer release, if any.

    Args:
        current: Installed version.
        now: Current time, as ``time.time()``; injectable for tests.

    Returns:
        UpdateInfo | None: The newer release, or None when there is none or
        it cannot be known.
    """
    latest = latest_release(now=now)
    if latest is None or not is_newer(latest, current):
        return None
    return UpdateInfo(current=current, latest=latest, upgrade_command=upgrade_command())


# ///////////////////////////////////////////////////////////////
# PRIVATE HELPERS
# ///////////////////////////////////////////////////////////////


def _as_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _read_cache() -> dict[str, object]:
    try:
        data = json.loads(update_check_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_cache(data: dict[str, object]) -> None:
    try:
        target = update_check_file()
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(data), encoding="utf-8")
        os.replace(temporary, target)
    except OSError:
        pass


def _fetch_latest() -> str | None:
    # Imported here: urllib and http.client cost ~85 ms at import.
    import http.client
    import urllib.request

    request = urllib.request.Request(
        _PYPI_URL,
        headers={"Accept": "application/json", "User-Agent": PACKAGE_NAME},
    )
    try:
        # B310/S310 waived: the URL is a constant https address.
        with urllib.request.urlopen(  # noqa: S310  # nosec B310
            request, timeout=_TIMEOUT_SECONDS
        ) as response:
            payload = json.loads(response.read(_MAX_RESPONSE_BYTES))
        version = payload["info"]["version"]
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        return None
    return version if isinstance(version, str) else None


__all__ = [
    "PACKAGE_NAME",
    "UpdateInfo",
    "check_for_update",
    "is_newer",
    "latest_release",
    "upgrade_command",
]
