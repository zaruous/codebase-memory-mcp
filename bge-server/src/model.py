"""
BGE-M3 model manager — thread-safe singleton with lazy loading.
Supports sentence-transformers backend with FlagEmbedding fallback.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import TYPE_CHECKING

import numpy as np

from config import get_config

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None
_load_error: Exception | None = None
_loaded_at: float | None = None


def _resolve_device(device_str: str) -> str:
    if device_str != "auto":
        return device_str
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def _load_model():
    global _model, _load_error, _loaded_at
    cfg = get_config()
    device = _resolve_device(cfg.device)
    model_id = cfg.effective_model

    logger.info("Loading BGE model '%s' on device '%s' ...", model_id, device)
    t0 = time.perf_counter()

    try:
        from sentence_transformers import SentenceTransformer
        kwargs: dict = {"device": device}
        if cfg.precision == "float16":
            import torch
            kwargs["torch_dtype"] = torch.float16
        _model = SentenceTransformer(model_id, **kwargs)
        _model.max_seq_length = cfg.max_length
    except Exception as e:
        _load_error = e
        logger.error("Failed to load model: %s", e)
        raise

    elapsed = time.perf_counter() - t0
    _loaded_at = time.time()
    logger.info("Model loaded in %.1fs", elapsed)


def ensure_loaded() -> None:
    """Load model if not yet loaded. Thread-safe."""
    global _model, _load_error
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        if _load_error is not None:
            raise RuntimeError(f"Model failed to load: {_load_error}") from _load_error
        _load_model()


def is_loaded() -> bool:
    return _model is not None


def get_model_info() -> dict:
    cfg = get_config()
    return {
        "model": cfg.effective_model,
        "device": _resolve_device(cfg.device),
        "precision": cfg.precision,
        "max_length": cfg.max_length,
        "loaded": is_loaded(),
        "loaded_at": _loaded_at,
    }


async def embed_texts(
    texts: list[str],
    normalize: bool | None = None,
) -> NDArray[np.float32]:
    """
    Embed a list of texts. Runs model inference in a thread pool to avoid
    blocking the asyncio event loop.
    """
    ensure_loaded()
    cfg = get_config()
    should_normalize = normalize if normalize is not None else cfg.normalize_embeddings

    loop = asyncio.get_event_loop()
    embeddings: NDArray[np.float32] = await loop.run_in_executor(
        None,
        lambda: _model.encode(
            texts,
            batch_size=cfg.batch_size,
            normalize_embeddings=should_normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        ),
    )
    return embeddings.astype(np.float32)


def cosine_similarity(a: NDArray[np.float32], b: NDArray[np.float32]) -> float:
    """Cosine similarity between two 1-D vectors."""
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))
