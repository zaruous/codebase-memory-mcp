"""
BGE Standalone Web Server — entry point.

Usage:
  python main.py [--host 0.0.0.0] [--port 8765] [--model-path /path/to/bge-m3]
  ./bge-server                         (packaged exe)
  BGE_MODEL_PATH=/models/bge-m3 ./bge-server
"""
from __future__ import annotations

import argparse
import logging
import sys
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from config import Config, set_config, get_config
import model as mdl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bge-server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    logger.info("BGE Server starting — model: %s", cfg.effective_model)

    # Load model in background thread so startup doesn't block
    t = threading.Thread(target=_preload_model, daemon=True)
    t.start()

    yield

    logger.info("BGE Server shutting down")


def _preload_model():
    try:
        mdl.ensure_loaded()
    except Exception as e:
        logger.error("Model preload failed: %s", e)


def build_app() -> FastAPI:
    app = FastAPI(
        title="BGE Embedding Server",
        description="Standalone BGE-M3 embedding service with OpenAI-compatible API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = build_app()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="bge-server",
        description="BGE-M3 standalone embedding web server",
    )
    p.add_argument("--host", default=None, help="Bind host (default: 0.0.0.0)")
    p.add_argument("--port", type=int, default=None, help="Port (default: 8765)")
    p.add_argument("--model-name", default=None, help="HuggingFace model ID")
    p.add_argument("--model-path", default=None, help="Local model directory path")
    p.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda", "mps"],
        default=None,
        help="Inference device (default: auto)",
    )
    p.add_argument(
        "--precision",
        choices=["float32", "float16", "int8"],
        default=None,
        help="Model precision (default: float32)",
    )
    p.add_argument("--max-length", type=int, default=None, help="Max token length")
    p.add_argument("--batch-size", type=int, default=None, help="Inference batch size")
    p.add_argument(
        "--no-normalize",
        action="store_true",
        help="Disable embedding normalization",
    )
    p.add_argument("--log-level", default=None, choices=["debug", "info", "warning", "error"])
    return p.parse_args()


def main():
    args = parse_args()

    cfg = get_config()

    # Override config from CLI args
    if args.host:
        cfg.host = args.host
    if args.port:
        cfg.port = args.port
    if args.model_name:
        cfg.model_name = args.model_name
    if args.model_path:
        cfg.model_path = args.model_path
    if args.device:
        cfg.device = args.device
    if args.precision:
        cfg.precision = args.precision
    if args.max_length:
        cfg.max_length = args.max_length
    if args.batch_size:
        cfg.batch_size = args.batch_size
    if args.no_normalize:
        cfg.normalize_embeddings = False
    if args.log_level:
        cfg.log_level = args.log_level
        logging.getLogger().setLevel(cfg.log_level.upper())

    set_config(cfg)

    logger.info("Starting BGE Server on http://%s:%d", cfg.host, cfg.port)
    logger.info("Model: %s | Device: %s | Precision: %s", cfg.effective_model, cfg.device, cfg.precision)
    logger.info("API docs: http://%s:%d/docs", cfg.host, cfg.port)

    uvicorn.run(
        app,
        host=cfg.host,
        port=cfg.port,
        log_level=cfg.log_level,
        workers=1,  # single worker — model is in-process singleton
    )


if __name__ == "__main__":
    main()
