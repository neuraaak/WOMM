"""Tests for project validation utils."""

from __future__ import annotations

import pytest

from womm.utils.project.validation_utils import validate_project_type


def test_validate_project_type_accepts_a_catalog_identifier() -> None:
    validate_project_type("python")


def test_validate_project_type_accepts_a_legacy_alias() -> None:
    validate_project_type("react")


def test_validate_project_type_rejects_empty_type() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_project_type("")


# The "unknown type" check was moved to ProjectValidationService.validate_project_type
# (service layer) to respect the utils -> services import-linter layering contract.
