# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# This is a PyInstaller spec file. It is used to bundle the Python backend
# into a single executable that can be shipped with the Electron app.

# The project_root is the 'fourdst/' directory that contains 'electron/', 'fourdst/', etc.
# SPECPATH is a variable provided by PyInstaller that contains the absolute path
# to the directory containing the spec file.
project_root = Path(SPECPATH).parent

# We need to add the project root to the path so that PyInstaller can find the 'fourdst' module.
sys.path.insert(0, str(project_root))

# The main script to be bundled.
analysis = Analysis(['bridge.py'],
               pathex=[str(project_root)],
               binaries=[],
               # Add any modules that PyInstaller might not find automatically.
               hiddenimports=['docker'],
               hookspath=[],
               runtime_hooks=[],
               excludes=[],
               win_no_prefer_redirects=False,
               win_private_assemblies=False,
               cipher=None,
               noarchive=False)

pyz = PYZ(analysis.pure, analysis.zipped_data,
             cipher=None)

exe = EXE(pyz, 
          analysis.scripts,
          [],
          exclude_binaries=True,
          name='fourdst-backend',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT(exe,
               analysis.binaries,
               analysis.zipfiles,
               analysis.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='fourdst-backend')
