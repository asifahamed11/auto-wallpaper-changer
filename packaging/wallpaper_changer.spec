# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path


root = Path(SPECPATH).parent
src = root / "src"
assets = src / "wallpaper_changer" / "assets"

a = Analysis(
    [str(src / "wallpaper_changer" / "app.py")],
    pathex=[str(src)],
    binaries=[],
    datas=[
        (str(assets / "icon.svg"), "wallpaper_changer/assets"),
        (str(assets / "icon.png"), "wallpaper_changer/assets"),
        (str(assets / "icon.ico"), "wallpaper_changer/assets"),
    ],
    hiddenimports=["PIL._tkinter_finder", "comtypes.stream"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AutoWallpaperChanger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(assets / "icon.ico"),
    version=str(root / "packaging" / "version_info.txt"),
    manifest=str(root / "packaging" / "app.manifest"),
)

