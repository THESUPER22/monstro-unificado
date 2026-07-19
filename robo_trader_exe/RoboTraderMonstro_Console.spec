# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['monstro_com_console.py'],
    pathex=[],
    binaries=[],
    datas=[('config_win_v2.json', '.'), ('config.json', '.'), ('EA_BookData_Universal.mq5', '.'), ('modelo_monstro.h5', '.'), ('modelo_monstro_win.h5', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RoboTraderMonstro_Console',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
