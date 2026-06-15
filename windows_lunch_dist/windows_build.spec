# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Windows onefile build of 하태욱 프로그램.

Usage:
    pyinstaller windows_build.spec --noconfirm --clean
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
        'pkg_resources',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='하태욱 프로그램',
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
    icon=os.path.join(SPECPATH, 'assets', 'icons', 'app_icon.ico'),
    manifest=os.path.join(SPECPATH, 'windows_manifest.xml'),
    version=os.path.join(SPECPATH, 'windows_version_info.txt'),
)
