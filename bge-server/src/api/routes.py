"""All API route handlers."""
from __future__ import annotations

import logging

import numpy as np
from fastapi import APIRouter, HTTPException

import model as mdl
from api.schemas import (
    EmbedBatchRequest,
    EmbedBatchResponse,
    EmbedRequest,
    EmbedResponse,
    HealthResponse,
    OpenAIEmbedRequest,
    OpenAIEmbedResponse,
    OpenAIEmbeddingObject,
    OpenAIUsage,
    SearchHit,
    SearchRequest,
    SearchResponse,
    SimilarityRequest,
    SimilarityResponse,
)
from config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["status"])
async def health():
    info = mdl.get_model_info()
    return HealthResponse(
        status="ok" if info["loaded"] else "loading",
        model=info["model"],
        loaded=info["loaded"],
        device=info["device"],
        precision=info["precision"],
    )


@router.get("/info", tags=["status"])
async def info():
    return mdl.get_model_info()


# ── Embed ─────────────────────────────────────────────────────────────────────

@router.post("/embed", response_model=EmbedResponse, tags=["embedding"])
async def embed(req: EmbedRequest):
    try:
        vecs = await mdl.embed_texts([req.text], normalize=req.normalize)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    vec = vecs[0].tolist()
    return EmbedResponse(
        embedding=vec,
        dim=len(vec),
        model=get_config().effective_model,
    )


@router.post("/embed/batch", response_model=EmbedBatchResponse, tags=["embedding"])
async def embed_batch(req: EmbedBatchRequest):
    try:
        vecs = await mdl.embed_texts(req.texts, normalize=req.normalize)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    embeddings = vecs.tolist()
    return EmbedBatchResponse(
        embeddings=embeddings,
        dim=vecs.shape[1] if vecs.ndim == 2 else len(embeddings[0]),
        count=len(embeddings),
        model=get_config().effective_model,
    )


# ── OpenAI-compatible ─────────────────────────────────────────────────────────

@router.post("/v1/embeddings", response_model=OpenAIEmbedResponse, tags=["openai"])
async def openai_embeddings(req: OpenAIEmbedRequest):
    texts = [req.input] if isinstance(req.input, str) else req.input
    try:
        vecs = await mdl.embed_texts(texts)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    data = [
        OpenAIEmbeddingObject(embedding=vec.tolist(), index=i)
        for i, vec in enumerate(vecs)
    ]
    total_tokens = sum(len(t.split()) for t in texts)
    return OpenAIEmbedResponse(
        data=data,
        model=get_config().effective_model,
        usage=OpenAIUsage(prompt_tokens=total_tokens, total_tokens=total_tokens),
    )


# ── Similarity ────────────────────────────────────────────────────────────────

@router.post("/similarity", response_model=SimilarityResponse, tags=["search"])
async def similarity(req: SimilarityRequest):
    try:
        vecs = await mdl.embed_texts([req.text_a, req.text_b], normalize=req.normalize)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    score = mdl.cosine_similarity(vecs[0], vecs[1])
    return SimilarityResponse(score=score, model=get_config().effective_model)


# ── Semantic search ───────────────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse, tags=["search"])
async def search(req: SearchRequest):
    all_texts = [req.query] + req.documents
    try:
        vecs = await mdl.embed_texts(all_texts, normalize=req.normalize)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    query_vec = vecs[0]
    doc_vecs = vecs[1:]

    # Cosine similarity via dot product (already normalized by embed_texts default)
    scores: np.ndarray = doc_vecs @ query_vec

    top_k = min(req.top_k, len(req.documents))
    top_indices = np.argsort(scores)[::-1][:top_k]

    hits = [
        SearchHit(
            index=int(idx),
            score=float(scores[idx]),
            text=req.documents[idx],
        )
        for idx in top_indices
    ]
    return SearchResponse(hits=hits, query=req.query, model=get_config().effective_model)
