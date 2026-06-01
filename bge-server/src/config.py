"""
Configuration for BGE standalone web server.
All settings can be overridden via environment variables or CLI args.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # Server
    host: str = field(default_factory=lambda: os.environ.get("BGE_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.environ.get("BGE_PORT", "8765")))
    workers: int = field(default_factory=lambda: int(os.environ.get("BGE_WORKERS", "1")))

    # Model
    model_name: str = field(
        default_factory=lambda: os.environ.get("BGE_MODEL_NAME", "BAAI/bge-m3")
    )
    model_path: str | None = field(
        default_factory=lambda: os.environ.get("BGE_MODEL_PATH")
    )
    device: str = field(
        default_factory=lambda: os.environ.get("BGE_DEVICE", "auto")
    )
    # "float32", "float16", "int8"
    precision: str = field(
        default_factory=lambda: os.environ.get("BGE_PRECISION", "float32")
    )

    # Inference
    max_length: int = field(
        default_factory=lambda: int(os.environ.get("BGE_MAX_LENGTH", "8192"))
    )
    batch_size: int = field(
        default_factory=lambda: int(os.environ.get("BGE_BATCH_SIZE", "32"))
    )
    normalize_embeddings: bool = field(
        default_factory=lambda: os.environ.get("BGE_NORMALIZE", "true").lower() == "true"
    )

    # Logging
    log_level: str = field(
        default_factory=lambda: os.environ.get("BGE_LOG_LEVEL", "info")
    )

    @property
    def effective_model(self) -> str:
        """Return model path if set, otherwise model name for HuggingFace download."""
        return self.model_path if self.model_path else self.model_name


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(cfg: Config) -> None:
    global _config
    _config = cfg
