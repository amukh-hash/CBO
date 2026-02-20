# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['scripts/run_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/ui/templates', 'app/ui/templates'),
        ('app/ui/static', 'app/ui/static'),
    ],
    hiddenimports=[
        'cryptography',
        'cryptography.hazmat.bindings._rust',
        'keyring.backends.macOS',
        'keyring.backends.Windows',
        'jinja2',
        'pyotp',
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
    name='cb-organizer-app',
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
)
