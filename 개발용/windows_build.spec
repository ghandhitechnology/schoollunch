# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a fast-starting Windows onedir build.

Usage:
    pyinstaller windows_build.spec --noconfirm --clean

The onedir layout intentionally avoids onefile's extraction step on every
launch. This uses less CPU and temporary-disk I/O on lower-end PCs.
"""
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath(SPECPATH)],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[
        'PIL._tkinter_finder',
        'pystray._win32',
    ],
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
    name='하태욱 프로그램',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(SPECPATH, 'assets', 'icons', 'app_icon.ico'),
    manifest=os.path.join(SPECPATH, 'windows_manifest.xml'),
    version=os.path.join(SPECPATH, 'windows_version_info.txt'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='하태욱 프로그램',
)
