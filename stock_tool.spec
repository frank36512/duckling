# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# 项目路径
project_root = Path('E:/stock_tool')

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('config/config.yaml', 'config'),
        ('docs/*.md', 'docs'),
    ],
    hiddenimports=[
        'PyQt5',
        'pandas',
        'numpy',
        'akshare',
        'backtrader',
        'matplotlib',
        'cryptography',
        'yaml',
        'sqlite3',
        'datetime',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'IPython',
        'jupyter',
        'notebook',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='小鸭量化',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/duck.ico',
)
