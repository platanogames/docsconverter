"""Resolve resource paths for both development and frozen (PyInstaller) mode."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_base_path() -> Path:
    """Return the base path for bundled resources.

    - Frozen mode  : sys._MEIPASS  (temporary extraction folder)
    - Dev mode     : project root  (parent of the ``app`` package)
    """
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent.parent


def get_resource_path(*parts: str) -> Path:
    """Build a path relative to the base resource directory.

    Usage::

        get_resource_path("configs", "profiles", "default.yaml")
        get_resource_path("templates", "base.html")
        get_resource_path("pandoc", "pandoc.exe")
    """
    return get_base_path() / Path(*parts)


def get_default_pandoc_path() -> Path:
    """Return the path to the bundled pandoc binary."""
    if is_frozen():
        return get_resource_path("pandoc", "pandoc.exe")
    return get_base_path() / "pandoc-3.9-windows-x86_64" / "pandoc-3.9" / "pandoc.exe"


def get_configs_dir() -> Path:
    """Return the path to the configs directory."""
    return get_resource_path("configs")


def get_templates_dir() -> Path:
    """Return the path to the templates directory."""
    return get_resource_path("templates")


def get_styles_dir() -> Path:
    """Return the path to the styles directory."""
    return get_resource_path("styles")


def get_user_data_dir() -> Path:
    """Return a writable directory for user data (logs, history, build outputs).

    - Frozen mode  : directory where the .exe lives
    - Dev mode     : project root
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return get_base_path()
