# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for bge-server.
Produces a single onedir distribution (recommended for large ML deps).
Use --onefile flag in build.sh for a single exe (much slower startup).

Build:  pyinstaller bge_server.spec --clean
Output: dist/bge-server/bge-server  (Linux/Mac)
        dist/bge-server/bge-server.exe  (Windows)
"""
import sys
from pathlib import Path

SRC = str(Path("src").resolve())
sys.path.insert(0, SRC)

block_cipher = None

a = Analysis(
    [str(Path(SRC) / "main.py")],
    pathex=[SRC],
    binaries=[],
    datas=[
        # Include sentence-transformers data files (tokenizer configs etc.)
        (
            "__import__('sentence_transformers').__path__[0]",
            "sentence_transformers",
        ),
    ],
    hiddenimports=[
        # FastAPI / uvicorn internals
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.loops.uvloop",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "fastapi.middleware.cors",
        # Pydantic
        "pydantic",
        "pydantic.v1",
        # PyTorch / transformers
        "torch",
        "torch.nn",
        "torch.nn.functional",
        "transformers",
        "transformers.models.xlm_roberta",
        "transformers.tokenization_utils",
        "sentence_transformers",
        "sentence_transformers.models",
        # NumPy
        "numpy",
        "numpy.core._methods",
        "numpy.lib.format",
        # Project modules
        "config",
        "model",
        "api",
        "api.routes",
        "api.schemas",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy unused ML libraries
        "tensorflow",
        "keras",
        "jax",
        "flax",
        "cv2",
        "PIL",
        "matplotlib",
        "scipy",
        "sklearn",
        "pandas",
        "IPython",
        "jupyter",
        "notebook",
    ],
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
    name="bge-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="bge-server",
)
