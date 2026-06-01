"""Request / response Pydantic schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Embed ────────────────────────────────────────────────────────────────────

class EmbedRequest(BaseModel):
    text: str = Field(..., description="Text to embed")
    normalize: bool | None = Field(None, description="Override global normalize setting")


class EmbedResponse(BaseModel):
    embedding: list[float]
    dim: int
    model: str


# ── Embed batch ──────────────────────────────────────────────────────────────

class EmbedBatchRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=512)
    normalize: bool | None = None


class EmbedBatchResponse(BaseModel):
    embeddings: list[list[float]]
    dim: int
    count: int
    model: str


# ── OpenAI-compatible /v1/embeddings ────────────────────────────────────────

class OpenAIEmbedRequest(BaseModel):
    input: str | list[str]
    model: str = "BAAI/bge-m3"
    encoding_format: Literal["float", "base64"] = "float"


class OpenAIEmbeddingObject(BaseModel):
    object: Literal["embedding"] = "embedding"
    embedding: list[float]
    index: int


class OpenAIUsage(BaseModel):
    prompt_tokens: int
    total_tokens: int


class OpenAIEmbedResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[OpenAIEmbeddingObject]
    model: str
    usage: OpenAIUsage


# ── Similarity ───────────────────────────────────────────────────────────────

class SimilarityRequest(BaseModel):
    text_a: str
    text_b: str
    normalize: bool | None = None


class SimilarityResponse(BaseModel):
    score: float = Field(..., ge=-1.0, le=1.0)
    model: str


# ── Search ───────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    documents: list[str] = Field(..., min_length=1, max_length=1024)
    top_k: int = Field(5, ge=1, le=100)
    normalize: bool | None = None


class SearchHit(BaseModel):
    index: int
    score: float
    text: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    query: str
    model: str


# ── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: Literal["ok", "loading", "error"]
    model: str
    loaded: bool
    device: str
    precision: str
    version: str = "1.0.0"
