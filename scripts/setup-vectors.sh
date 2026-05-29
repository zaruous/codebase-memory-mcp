#!/usr/bin/env bash
# setup-vectors.sh — Prepare BGE-M3 pretrained vectors for building.
#
# Priority:
#   1. Already present  → nothing to do
#   2. --extract flag   → run extraction via TEI Docker or direct Python
#   3. Default          → download pre-built code_vectors.bin from GitHub Releases
#
# Usage:
#   scripts/setup-vectors.sh                     # download (default)
#   scripts/setup-vectors.sh --extract           # extract with TEI (Docker required)
#   scripts/setup-vectors.sh --extract --no-tei  # extract via Python only (slow on CPU)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VECTORS_DIR="vendored/bge_m3_real"
VECTORS_BIN="$VECTORS_DIR/code_vectors.bin"

# ── GitHub Release asset URL ──────────────────────────────────────────────
RELEASE_TAG="bge-m3-vectors-v1"
# Derive repo from git remote so forks automatically use the right URL
REPO=$(git remote get-url origin 2>/dev/null \
       | sed 's|https://github.com/||;s|git@github.com:||;s|\.git$||' \
       || echo "zaruous/codebase-memory-mcp")
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${RELEASE_TAG}/code_vectors.bin"

# Allow env override for self-hosted or mirror
VECTORS_URL="${CBM_VECTORS_URL:-$DOWNLOAD_URL}"

# ── Parse args ────────────────────────────────────────────────────────────
EXTRACT=false
NO_TEI=false
for arg in "$@"; do
  case "$arg" in
    --extract) EXTRACT=true ;;
    --no-tei)  NO_TEI=true ;;
  esac
done

# ── Step 0: already present? ──────────────────────────────────────────────
if [ -f "$VECTORS_BIN" ]; then
  SIZE=$(du -sh "$VECTORS_BIN" | cut -f1)
  echo "vectors already present: $VECTORS_BIN ($SIZE) — nothing to do."
  exit 0
fi

mkdir -p "$VECTORS_DIR"

# ── Step 1: extract mode ──────────────────────────────────────────────────
if [ "$EXTRACT" = true ]; then
  echo "=== BGE-M3 vector extraction ==="

  if [ "$NO_TEI" = false ] && command -v docker &>/dev/null; then
    # Detect CUDA compute capability for TEI image tag
    SM="86"
    if command -v nvidia-smi &>/dev/null; then
      SM=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null \
           | head -1 | tr -d '.' || echo "86")
    fi
    TEI_IMAGE="ghcr.io/huggingface/text-embeddings-inference:${SM}-1.9"

    echo "starting TEI ($TEI_IMAGE)..."
    docker run -d --name tei-bge-m3-setup --gpus all -p 8080:80 \
      "$TEI_IMAGE" \
      --model-id BAAI/bge-m3 --pooling cls --dtype float16

    echo "waiting for TEI to be ready..."
    until docker logs tei-bge-m3-setup 2>&1 | grep -q "Ready"; do sleep 5; done

    python3 scripts/extract_nomic_vectors.py \
      --output-dir "$VECTORS_DIR" \
      --tei-url http://localhost:8080

    docker stop tei-bge-m3-setup && docker rm tei-bge-m3-setup

    # Regenerate headers if bin was written but text files failed (Windows CP949 issue)
    if [ ! -f "$VECTORS_DIR/code_tokens.h" ]; then
      python3 scripts/write_headers.py
    fi
  else
    echo "extracting via Python (no Docker / --no-tei)..."
    DEVICE="cpu"
    if python3 -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
      DEVICE="cuda"
    elif python3 -c "import torch; exit(0 if torch.backends.mps.is_available() else 1)" 2>/dev/null; then
      DEVICE="mps"
    fi
    echo "device: $DEVICE"
    python3 scripts/extract_nomic_vectors.py \
      --output-dir "$VECTORS_DIR" \
      --device "$DEVICE"
  fi

  echo "extraction complete."
  exit 0
fi

# ── Step 2: download from GitHub Releases ────────────────────────────────
echo "=== Downloading BGE-M3 vectors ==="
echo "source: $VECTORS_URL"

TMP_BIN="$VECTORS_DIR/code_vectors.bin.tmp"

if command -v curl &>/dev/null; then
  curl -L --progress-bar -o "$TMP_BIN" "$VECTORS_URL"
elif command -v wget &>/dev/null; then
  wget -O "$TMP_BIN" "$VECTORS_URL"
else
  echo "error: curl or wget required" >&2
  exit 1
fi

mv "$TMP_BIN" "$VECTORS_BIN"
echo "downloaded: $VECTORS_BIN ($(du -sh "$VECTORS_BIN" | cut -f1))"

# Regenerate headers from downloaded bin
python3 scripts/write_headers.py

echo ""
echo "done. run 'make -f Makefile.cbm cbm' to build."
