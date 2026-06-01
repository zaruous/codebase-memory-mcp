#!/usr/bin/env bash
# Build bge-server standalone executable for Linux / macOS
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"
VENV_DIR=".venv-build"
ONEFILE="${ONEFILE:-0}"   # set ONEFILE=1 for single-file exe (slow startup, 1-2GB)

echo "==> BGE Server build starting"
echo "    Python: $($PYTHON --version)"
echo "    Mode: $([ "$ONEFILE" = "1" ] && echo onefile || echo onedir)"

# ── Virtual environment ──────────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "==> Creating build venv"
    "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Installing dependencies"
pip install --quiet --upgrade pip
pip install --quiet -r requirements-dev.txt

# ── Torch: CPU-only for smaller build unless CUDA requested ─────────────────
if [ "${BGE_CUDA:-0}" = "1" ]; then
    echo "==> Installing PyTorch with CUDA support"
    pip install --quiet torch --index-url https://download.pytorch.org/whl/cu121
else
    echo "==> Installing PyTorch (CPU-only, smaller build)"
    pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu
fi

# ── PyInstaller build ────────────────────────────────────────────────────────
echo "==> Running PyInstaller"

EXTRA_ARGS=""
if [ "$ONEFILE" = "1" ]; then
    EXTRA_ARGS="--onefile"
fi

pyinstaller bge_server.spec --clean --noconfirm $EXTRA_ARGS

# ── Output summary ───────────────────────────────────────────────────────────
DIST_DIR="dist/bge-server"
EXE="$DIST_DIR/bge-server"

if [ -f "$EXE" ]; then
    SIZE=$(du -sh "$EXE" | cut -f1)
    echo ""
    echo "==> Build complete"
    echo "    Binary: $EXE ($SIZE)"
    echo ""
    echo "Usage:"
    echo "  $EXE --help"
    echo "  $EXE --port 8765 --model-path /path/to/bge-m3"
    echo "  BGE_MODEL_PATH=/models/bge-m3 $EXE"
else
    echo "==> Build complete: dist/bge-server/ directory"
    echo "    Run: $DIST_DIR/bge-server --help"
fi
