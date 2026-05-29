# setup-vectors.ps1 — Prepare BGE-M3 pretrained vectors for building on Windows.
#
# Priority:
#   1. Already present  -> nothing to do
#   2. -Extract flag    -> run extraction via TEI Docker or direct Python
#   3. Default          -> download pre-built code_vectors.bin from GitHub Releases
#
# Usage:
#   scripts\setup-vectors.ps1                    # download (default)
#   scripts\setup-vectors.ps1 -Extract           # extract with TEI (Docker required)
#   scripts\setup-vectors.ps1 -Extract -NoTei    # extract via Python only

param(
    [switch]$Extract,
    [switch]$NoTei
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$VectorsDir = Join-Path $Root "vendored\bge_m3_real"
$VectorsBin = Join-Path $VectorsDir "code_vectors.bin"

# ── GitHub Release asset URL ──────────────────────────────────────────────
$ReleaseTag = "bge-m3-vectors-v1"
# Derive repo from git remote so forks automatically use the right URL
$RemoteUrl = (git remote get-url origin 2>$null) -replace "https://github.com/","" `
                                                  -replace "git@github.com:","" `
                                                  -replace "\.git$",""
$Repo = if ($RemoteUrl) { $RemoteUrl } else { "zaruous/codebase-memory-mcp" }
$DefaultUrl = "https://github.com/$Repo/releases/download/$ReleaseTag/code_vectors.bin"
$VectorsUrl = if ($env:CBM_VECTORS_URL) { $env:CBM_VECTORS_URL } else { $DefaultUrl }

# ── Step 0: already present? ─────────────────────────────────────────────
if (Test-Path $VectorsBin) {
    $size = [math]::Round((Get-Item $VectorsBin).Length / 1MB, 1)
    Write-Host "vectors already present: $VectorsBin ($size MB) — nothing to do."
    exit 0
}

New-Item -ItemType Directory -Force -Path $VectorsDir | Out-Null

# ── Step 1: extract mode ──────────────────────────────────────────────────
if ($Extract) {
    Write-Host "=== BGE-M3 vector extraction ==="

    $dockerOk = $null -ne (Get-Command docker -ErrorAction SilentlyContinue)

    if (-not $NoTei -and $dockerOk) {
        # Detect CUDA SM for TEI image tag
        $sm = "86"
        try {
            $cap = & nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>$null |
                   Select-Object -First 1
            if ($cap) { $sm = $cap -replace "\.", "" }
        } catch {}
        $teiImage = "ghcr.io/huggingface/text-embeddings-inference:${sm}-1.9"

        Write-Host "starting TEI ($teiImage)..."
        docker run -d --name tei-bge-m3-setup --gpus all -p 8080:80 `
            $teiImage `
            --model-id BAAI/bge-m3 --pooling cls --dtype float16

        Write-Host "waiting for TEI to be ready..."
        do {
            Start-Sleep 5
            $logs = docker logs tei-bge-m3-setup 2>&1
        } until ($logs -match "Ready")

        python scripts/extract_nomic_vectors.py `
            --output-dir $VectorsDir `
            --tei-url http://localhost:8080

        docker stop tei-bge-m3-setup | Out-Null
        docker rm tei-bge-m3-setup | Out-Null

        # Regenerate headers if text files failed (CP949 issue)
        if (-not (Test-Path (Join-Path $VectorsDir "code_tokens.h"))) {
            python scripts/write_headers.py
        }
    } else {
        Write-Host "extracting via Python (no Docker / -NoTei)..."
        $device = "cpu"
        $cudaOk = python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { $device = "cuda" }
        Write-Host "device: $device"
        python scripts/extract_nomic_vectors.py `
            --output-dir $VectorsDir `
            --device $device
    }

    Write-Host "extraction complete."
    exit 0
}

# ── Step 2: download from GitHub Releases ────────────────────────────────
Write-Host "=== Downloading BGE-M3 vectors ==="
Write-Host "source: $VectorsUrl"

$tmpBin = "$VectorsBin.tmp"

try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($VectorsUrl, $tmpBin)
} catch {
    # Fallback: Invoke-WebRequest (slower but more compatible)
    Invoke-WebRequest -Uri $VectorsUrl -OutFile $tmpBin -UseBasicParsing
}

Move-Item -Force $tmpBin $VectorsBin
$size = [math]::Round((Get-Item $VectorsBin).Length / 1MB, 1)
Write-Host "downloaded: $VectorsBin ($size MB)"

# Regenerate headers from downloaded bin
python scripts/write_headers.py

Write-Host ""
Write-Host "done. run 'make -f Makefile.cbm cbm' to build."
