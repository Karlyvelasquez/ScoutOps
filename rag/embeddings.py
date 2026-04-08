"""Sentence-transformers embedding wrapper with process-level model caching."""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> list[float]:
    """Embed one text string into a dense vector for retrieval."""
    model = _get_model()
    embedding = model.encode(text or "", normalize_embeddings=True)
    return embedding.tolist()
