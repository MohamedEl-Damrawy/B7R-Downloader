# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Velo Downloader.
# Build: python -m PyInstaller VeloDownloader.spec --noconfirm
# Output: dist\VeloDownloader\ (onedir) -> VeloDownloader.exe + _internal\
# NOTE: keep versions in sync with APP_VERSION in app/core/constants.py.

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('vendor', 'vendor'),
        ('licenses', 'licenses'),
        ('LICENSE', '.'),
    ],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='VeloDownloader',
    icon='resources\\icons\\app.ico',
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='VeloDownloader',
)
