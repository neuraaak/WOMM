#!/usr/bin/env python3
# ///////////////////////////////////////////////////////////////
# TEST SHARED CONFIGS HELPERS - Classmethod coverage batch
# Project: Works On My Machine
# ///////////////////////////////////////////////////////////////

"""
Tests for the small ``@classmethod``/``@staticmethod`` helpers on frozen
config dataclasses under ``shared/configs/``.

These classes hold only static ``ClassVar`` data plus pure lookup helpers
(dict/set membership, string formatting) — no I/O, no mocking needed.
"""

from __future__ import annotations

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Local imports
from womm.shared.configs.context.context_file_types_config import (
    ContextFileTypesConfig,
)
from womm.shared.configs.context.context_limits_config import ContextLimitsConfig
from womm.shared.configs.context.context_paths_config import ContextPathsConfig
from womm.shared.configs.system.system_detector_config import (
    PackageManagerConfig,
    SystemDetectorConfig,
)
from womm.shared.configs.system.system_environment_config import (
    SystemEnvironmentConfig,
)

# ///////////////////////////////////////////////////////////////
# CONTEXT FILE TYPES CONFIG
# ///////////////////////////////////////////////////////////////


def test_get_file_type_known_extension():
    assert ContextFileTypesConfig.get_file_type(".png") == "image"


def test_get_file_type_is_case_insensitive():
    assert ContextFileTypesConfig.get_file_type(".PNG") == "image"


def test_get_file_type_unknown_extension_returns_none():
    assert ContextFileTypesConfig.get_file_type(".xyz") is None


def test_get_extensions_for_type_known_type():
    assert ".zip" in ContextFileTypesConfig.get_extensions_for_type("archive")


def test_get_extensions_for_type_unknown_type_returns_empty_set():
    assert ContextFileTypesConfig.get_extensions_for_type("unknown") == set()


def test_get_all_file_types_lists_categories():
    types = ContextFileTypesConfig.get_all_file_types()

    assert "image" in types
    assert "code" in types


def test_get_all_extensions_returns_a_copy():
    extensions = ContextFileTypesConfig.get_all_extensions()
    extensions["image"] = set()

    assert ".png" in ContextFileTypesConfig.FILE_TYPE_EXTENSIONS["image"]


# ///////////////////////////////////////////////////////////////
# CONTEXT LIMITS CONFIG
# ///////////////////////////////////////////////////////////////


def test_is_valid_registry_key_accepts_simple_name():
    assert ContextLimitsConfig.is_valid_registry_key("MyTool") is True


def test_is_valid_registry_key_rejects_empty():
    assert ContextLimitsConfig.is_valid_registry_key("") is False


def test_is_valid_registry_key_rejects_reserved_name():
    assert ContextLimitsConfig.is_valid_registry_key("CON") is False


def test_is_valid_registry_key_rejects_invalid_pattern():
    assert ContextLimitsConfig.is_valid_registry_key("bad key!") is False


def test_is_valid_script_extension_true_and_false():
    assert ContextLimitsConfig.is_valid_script_extension(".PY") is True
    assert ContextLimitsConfig.is_valid_script_extension(".sh") is False


def test_is_valid_icon_extension_true_and_false():
    assert ContextLimitsConfig.is_valid_icon_extension(".ICO") is True
    assert ContextLimitsConfig.is_valid_icon_extension(".gif") is False


def test_has_invalid_label_chars_detects_forbidden_character():
    assert ContextLimitsConfig.has_invalid_label_chars("My:Label") is True


def test_has_invalid_label_chars_accepts_clean_label():
    assert ContextLimitsConfig.has_invalid_label_chars("My Label") is False


# ///////////////////////////////////////////////////////////////
# CONTEXT PATHS CONFIG
# ///////////////////////////////////////////////////////////////


def test_get_registry_path_known_type():
    assert ContextPathsConfig.get_registry_path("directory") is not None


def test_get_registry_path_unknown_type_returns_none():
    assert ContextPathsConfig.get_registry_path("unknown") is None


def test_get_command_parameter_known_type():
    assert ContextPathsConfig.get_command_parameter("file") == "%1"


def test_get_command_parameter_unknown_type_defaults_to_v():
    assert ContextPathsConfig.get_command_parameter("unknown") == "%V"


def test_get_all_context_types_lists_directory():
    assert "directory" in ContextPathsConfig.get_all_context_types()


# ///////////////////////////////////////////////////////////////
# SYSTEM DETECTOR CONFIG
# ///////////////////////////////////////////////////////////////


def test_package_manager_config_get_by_platform_filters_correctly():
    windows_managers = PackageManagerConfig.get_by_platform("windows")

    assert "winget" in windows_managers
    assert "homebrew" not in windows_managers


def test_package_manager_config_platform_shortcuts():
    assert "winget" in PackageManagerConfig.get_windows_managers()
    assert "homebrew" in PackageManagerConfig.get_macos_managers()
    assert "apt" in PackageManagerConfig.get_linux_managers()


def test_system_detector_config_delegates_to_package_manager_config():
    assert (
        SystemDetectorConfig.get_windows_package_managers()
        == PackageManagerConfig.get_windows_managers()
    )
    assert (
        SystemDetectorConfig.get_macos_package_managers()
        == PackageManagerConfig.get_macos_managers()
    )
    assert (
        SystemDetectorConfig.get_linux_package_managers()
        == PackageManagerConfig.get_linux_managers()
    )


# ///////////////////////////////////////////////////////////////
# SYSTEM ENVIRONMENT CONFIG
# ///////////////////////////////////////////////////////////////


def test_get_shell_config_files_only_returns_existing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "womm.shared.configs.system.system_environment_config.Path.home",
        lambda: tmp_path,
    )
    (tmp_path / ".bashrc").write_text("", encoding="utf-8")

    files = SystemEnvironmentConfig.get_shell_config_files()

    assert len(files) == 1
    assert files[0].name == ".bashrc"


def test_get_shell_config_files_empty_home_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "womm.shared.configs.system.system_environment_config.Path.home",
        lambda: tmp_path,
    )

    assert SystemEnvironmentConfig.get_shell_config_files() == []
