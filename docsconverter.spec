# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for DocsConverter — single-folder distribution."""

import os
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH)

# ── Data files to bundle ────────────────────────────────────────────
datas = [
    # Pandoc binary
    (str(PROJECT_ROOT / "pandoc-3.9-windows-x86_64" / "pandoc-3.9" / "pandoc.exe"), "pandoc"),
    # Configuration profiles
    (str(PROJECT_ROOT / "configs"), "configs"),
    # Pandoc templates (HTML + LaTeX)
    (str(PROJECT_ROOT / "templates"), "templates"),
    # CSS stylesheets
    (str(PROJECT_ROOT / "styles"), "styles"),
]

a = Analysis(
    [str(PROJECT_ROOT / "launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "app",
        "app.core",
        "app.core.batch",
        "app.core.config",
        "app.core.history",
        "app.core.models",
        "app.core.paths",
        "app.core.pipeline",
        "app.core.preflight",
        "app.core.rules",
        "app.core.sanitizer",
        "app.core.sanitizer_config",
        "app.core.style_builder",
        "app.ui",
        "app.ui.window",
        # PySide6 — ensure the platform plugin is found
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "PIL",
        "IPython",
        "jupyter",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DocsConverter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # windowed app (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(PROJECT_ROOT / "version_info.txt") if (PROJECT_ROOT / "version_info.txt").exists() else None,
    icon=str(PROJECT_ROOT / "assets" / "icon.ico") if (PROJECT_ROOT / "assets" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DocsConverter",
)
