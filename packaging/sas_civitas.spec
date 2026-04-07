# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


block_cipher = None

_specpath = globals().get("SPECPATH")
if _specpath:
    ROOT = Path(_specpath).resolve().parent
else:
    ROOT = Path.cwd().resolve()
SRC = ROOT / "src"
APP_NAME = "SAS Civitas"

datas = [
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "config"), "config"),
    (str(ROOT / "data" / "AssistenteSocial.xlsx"), "data"),
]

a = Analysis(
    [str(ROOT / "gui.py")],
    pathex=[str(ROOT), str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(ROOT / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
