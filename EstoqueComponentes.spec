# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['estoque_componentes.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/robo_jp.png', 'assets')],
    hiddenimports=[
        'webview.platforms.edgechromium',
        'webview.platforms.winforms',
    ],
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
    [],
    exclude_binaries=True,
    name='EstoqueComponentes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EstoqueComponentes',
)
