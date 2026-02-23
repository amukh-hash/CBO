# -*- mode: python ; coding: utf-8 -*-

import os
spec_dir = os.path.abspath(SPECPATH)
root_dir = os.path.dirname(spec_dir)

a = Analysis(
    [os.path.join(spec_dir, 'run_app.py')],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(root_dir, 'app', 'ui', 'templates'), 'app/ui/templates'),
        (os.path.join(root_dir, 'app', 'ui', 'static'), 'app/ui/static'),
    ],
    hiddenimports=[
        'cryptography',
        'cryptography.hazmat.bindings._rust',
        'keyring.backends.macOS',
        'keyring.backends.Windows',
        'jinja2',
        'pyotp',
        'app.main',
        'uvicorn',
        'sqlite3',
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
