@echo off
REM Build bge-server standalone executable for Windows
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

set PYTHON=python
set VENV_DIR=.venv-build
set ONEFILE=0

echo =^> BGE Server build starting (Windows)
for /f "delims=" %%v in ('"%PYTHON%" --version 2^>^&1') do echo     Python: %%v

REM ── Virtual environment ──────────────────────────────────────────────────────
if not exist "%VENV_DIR%" (
    echo =^> Creating build venv
    "%PYTHON%" -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"

echo =^> Installing dependencies
pip install --quiet --upgrade pip
pip install --quiet -r requirements-dev.txt

REM ── Torch: CPU-only for smaller build ────────────────────────────────────────
if "%BGE_CUDA%"=="1" (
    echo =^> Installing PyTorch with CUDA support
    pip install --quiet torch --index-url https://download.pytorch.org/whl/cu121
) else (
    echo =^> Installing PyTorch (CPU-only)
    pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu
)

REM ── PyInstaller build ──────────────────────────────────────────────────────
echo =^> Running PyInstaller

set EXTRA_ARGS=
if "%ONEFILE%"=="1" set EXTRA_ARGS=--onefile

pyinstaller bge_server.spec --clean --noconfirm %EXTRA_ARGS%

echo.
echo =^> Build complete
echo     Binary: dist\bge-server\bge-server.exe
echo.
echo Usage:
echo   dist\bge-server\bge-server.exe --help
echo   dist\bge-server\bge-server.exe --port 8765 --model-path C:\models\bge-m3
