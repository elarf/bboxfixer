# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for bboxfixer-gui.exe
#
# Build with:
#   pyinstaller bboxfixer-gui.spec
#
# Or use the provided build_exe.bat (Windows).

a = Analysis(
    ['bboxfixer/__main_gui__.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'bboxfixer.gui',
        'bboxfixer.generator',
        'bboxfixer.models',
        'bboxfixer.printer',
        'bboxfixer.cli',
        'bboxfixer.parser',
        'bboxfixer.xml_models',
        'bboxfixer.xml_generator',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='bboxfixer-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # windowed – no console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
