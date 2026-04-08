"""Query helpers to retrieve relevant Reaction Commerce code chunks from Chroma."""

from __future__ import annotations

import logging
from typing import Any

from rag.embeddings import embed_text
from rag.vector_store import get_collection

logger = logging.getLogger(__name__)


def _distance_to_relevance(distance: float) -> float:
    return 1.0 / (1.0 + max(distance, 0.0))


def query_codebase(incident_type: str, description: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Search indexed code chunks and return ranked contextual snippets for triage."""
    try:
        query_text = f"incident_type: {incident_type}\ncontext: {description}".strip()
        if not query_text:
            return []

        collection = get_collection()
        query_embedding = embed_text(query_text)

        response = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        documents = (response.get("documents") or [[]])[0]
        metadatas = (response.get("metadatas") or [[]])[0]
        distances = (response.get("distances") or [[]])[0]

        if not documents:
            return []

        results: list[dict[str, Any]] = []
        for idx, content in enumerate(documents):
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            distance = distances[idx] if idx < len(distances) else 1.0
            results.append(
                {
                    "plugin_name": metadata.get("plugin_name", "unknown"),
                    "file_path": metadata.get("file_path", "unknown"),
                    "content": content,
                    "relevance_score": round(_distance_to_relevance(float(distance)), 4),
                }
            )

        return results
    except Exception:
        logger.exception("query_codebase failed", extra={"incident_type": incident_type})
        return []
