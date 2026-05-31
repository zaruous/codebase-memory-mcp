# syntax=docker/dockerfile:1
#
# codebase-memory-mcp — HTTP MCP server (코드 지식 그래프)
#
# Build:
#   docker build -t codebase-memory-mcp .
#   docker build --build-arg VERSION=0.6.1 -t codebase-memory-mcp .
#
# Run (HTTP 서버):
#   docker run -d -p 9748:9748 -v cbm-data:/data --name codebase-memory codebase-memory-mcp
#
# 저장소 인덱싱 (최초 1회, CLI 모드):
#   docker run --rm \
#     -v cbm-data:/data \
#     -v /path/to/project:/workspace:ro \
#     codebase-memory-mcp cli index_repository '{"path":"/workspace","name":"my-project"}'

ARG VERSION=0.10.1

# ── Stage 1: 바이너리 다운로드 ──────────────────────────────────────────────
FROM debian:bookworm-slim AS downloader
ARG VERSION
ARG TARGETARCH=amd64

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN ARCH="${TARGETARCH}" && \
    URL="https://github.com/DeusData/codebase-memory-mcp/releases/download/v${VERSION}/codebase-memory-mcp-linux-${ARCH}.tar.gz" && \
    echo "Downloading: $URL" && \
    curl -fsSL "$URL" -o /tmp/cbm.tar.gz && \
    tar -xzf /tmp/cbm.tar.gz -C /tmp/ && \
    chmod +x /tmp/codebase-memory-mcp && \
    rm /tmp/cbm.tar.gz

# ── Stage 2: 런타임 ──────────────────────────────────────────────────────────
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=downloader /tmp/codebase-memory-mcp /usr/local/bin/codebase-memory-mcp

# HOME을 /data로 설정 — SQLite DB, 캐시, 설정이 모두 /data 아래에 저장됨
ENV HOME=/data

RUN mkdir -p /data /workspace

# 9748: MCP HTTP 포트
EXPOSE 9748

# /data: 그래프 DB·캐시 영속 볼륨 마운트 위치
# /workspace: 인덱싱할 저장소 마운트 위치 (선택)
VOLUME ["/data"]

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:9748/mcp/health || exit 1

ENTRYPOINT ["codebase-memory-mcp"]
CMD ["--mcp-http=true", "--mcp-http-port=9748"]
